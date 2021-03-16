# %%
from graspologic.utils import import_graph, to_laplacian
from graspologic.embed.base import BaseSpectralEmbed
import numpy as np
import scipy
from joblib import delayed, Parallel
from sklearn.cluster import KMeans
from graspologic.plot import heatmap
from graspologic.utils import remap_labels
from sklearn.preprocessing import normalize, scale
from sklearn.utils.extmath import randomized_svd
from scipy.sparse.linalg import eigsh

np.set_printoptions(suppress=True)
import warnings

warnings.filterwarnings("ignore")

#%%


class CovariateAssistedEmbedding(BaseSpectralEmbed):
    """
        Perform Spectral Embedding on a graph with covariates, using the regularized graph Laplacian.

        The Covariate-Assisted Spectral Embedding is a k-dimensional Euclidean representation
        of a graph based on a function of its Laplacian and a vector of covariate features
        for each node.

        Parameters
        ----------
        embedding_alg : str, default = "assortative"
            Embedding algorithm to use:
            - "assortative": Embed ``L + a*X@X.T``. Better for assortative graphs.
            - "non-assortative": Embed ``L@L + a*X@X.T``. Better for non-assortative graphs.
            - "cca": Embed ``L@X``. Better for large graphs and faster.
    `
        n_components : int or None, default = None
            Desired dimensionality of output data. If "full",
            n_components must be <= min(X.shape). Otherwise, n_components must be
            < min(X.shape). If None, then optimal dimensions will be chosen by
            ``select_dimension`` using ``n_elbows`` argument.

        alpha : float, optional (default = None)
            Tuning parameter to use. Not used if embedding_alg == cca:
                -  None: tune the alpha-value by minimizing the k-means objective function.
                         Since this involves running k-means over a parameter space, this
                         will result in a slower algorithm in exchange for likely better
                         clustering.
                - float: use a particular alpha-value. Results in a much faster algorithm
                         (since we are not tuning with kmeans) in exchange for potentially
                         suboptimal clustering results.
                -    -1: Default to the ratio of the leading eigenvector of the Laplacian
                         to the leading eigenvector of the covariate matrix. This will
                         result in suboptimal clustering in exchange for increased
                         clustering speed.

        tuning_runs : int, optional (default = 100)
            If tuning alpha with k-means, this parameter determines the number of times
            k-means is run. Higher values are more computationally expensive in exchange
            for a finer-grained search of the parameter space (and better embedding).

        n_jobs : int, optional (default = -1)
            The number of parallel threads to use in K-means when calculating alpha.
            `-1` means using all processors.

        verbose : int, optional (default = 0)
            Verbosity mode.

        n_elbows : int, optional, default: 2
            If `n_components=None`, then compute the optimal embedding dimension using
            `select_dimension`. Otherwise, ignored.

        check_lcc : bool , optional (defult =True)
            Whether to check if input graph is connected. May result in non-optimal
            results if the graph is unconnected. Not checking for connectedness may
            result in faster computation.

        concat : bool, optional (default = False)
            If graph(s) are directed, whether to concatenate each graph's left and right
            (out and in) latent positions along axis 1.


        References
        ---------
        .. [1] Binkiewicz, N., Vogelstein, J. T., & Rohe, K. (2017). Covariate-assisted
        spectral clustering. Biometrika, 104(2), 361-377.
    """

    def __init__(
        self,
        n_components=None,
        embedding_alg="assortative",
        alpha=None,
        tuning_runs=20,
        n_jobs=-1,
        verbose=0,
        n_elbows=2,
        check_lcc=False,
        concat=False,
    ):
        super().__init__(
            algorithm="full",
            n_components=n_components,
            n_elbows=n_elbows,
            check_lcc=check_lcc,
            concat=concat,
        )
        if not isinstance(embedding_alg, str):
            raise TypeError("Embedding algorithm must be a string")
        if embedding_alg not in {"assortative", "non-assortative", "cca"}:
            msg = "embedding_alg must be in {assortative, non-assortative, cca}."
            raise ValueError(msg)
        self.embedding_alg = embedding_alg  # TODO: compute this automatically?

        if not ((alpha is None) or alpha == -1 or isinstance(alpha, float)):
            msg = "alpha must be in {None, float, -1}."
            raise TypeError(msg)

        if n_jobs is None:
            n_jobs = -1

        self.n_jobs = n_jobs
        self.alpha = alpha
        self.tuning_runs = tuning_runs
        self.verbose = verbose
        self.latent_right_ = None  # doesn't work for directed graphs atm
        self.is_fitted_ = False

    def fit(self, graph, covariates, y=None, labels=None):
        """
        Fit a CASE model to an input graph, along with its covariates. Depending on the
        embedding algorithm, we embed

        .. math:: L_ = LL + \alpha XX^T
        .. math:: L_ = L + \alpha XX^T
        .. math:: L_ = LX

        where :math:`\alpha` is a tuning parameter which makes the leading eigenvalues
        of the two summands the same. Here, :math:`L` is the regularized
        graph Laplacian, and :math:`X` is a matrix of covariates for each node.

        Parameters
        ----------
        graph : array-like or networkx.Graph
            Input graph to embed. See graspologic.utils.import_graph

        covariates : array-like, shape (n_vertices, n_covariates)
            Covariate matrix. Each node of the graph is associated with a set of
            `d` covariates. Row `i` of the covariates matrix corresponds to node
            `i`, and the number of columns are the number of covariates.

        y: Ignored

        Returns
        -------
        self : object
            Returns an instance of self.
        """

        # setup
        A = import_graph(graph)

        # center and scale covariates to unit norm
        covariates = normalize(covariates, axis=0)

        # save necessary params  # TODO: do this without saving potentially huge objects into `self`
        self._L = to_laplacian(A, form="R-DAD")
        self._R = np.shape(covariates)[1]
        self._X = covariates.copy()

        # change params based on tuning algorithm
        if self.embedding_alg == "cca":
            self._LL = self._L @ self._X
            self._reduce_dim(self._LL)
            self.is_fitted_ = True
            return self
        elif self.embedding_alg == "assortative":
            self._LL = self._L
            self._XXt = self._X @ self._X.T
            self.alpha_ = self._get_tuning_parameter()
        elif self.embedding_alg == "non-assortative":
            self._LL = self._L @ self._L
            self._XXt = self._X @ self._X.T
            self.alpha_ = self._get_tuning_parameter()

        self.latent_left_ = _embed(
            self.alpha_, self._LL, self._XXt, n_clusters=self.n_components
        )
        self.is_fitted_ = True
        return self

    def _get_tuning_parameter(self):
        """
        Find an alpha within a range which optimizes the k-means objective function on
        our embedding.

        Parameters
        ----------
        LL : array
            The squared regularized graph Laplacian
        XXt : array
            X@X.T, where X is the covariate matrix.

        Returns
        -------
        alpha : float
            Tuning parameter which normalizes LL and XXt.
        """
        # setup
        if isinstance(self.alpha, (int, float)) and self.alpha != -1:
            return self.alpha
        n_clusters = self.n_components  # number of clusters
        n_cov = self._R  # number of covariates

        # grab eigenvalues
        X_components = np.min([n_cov, n_clusters]) + 1
        _, X_eigvals, _ = randomized_svd(self._X, n_components=X_components)
        L_eigvals = np.flip(eigsh(self._L, k=n_clusters + 1, return_eigenvectors=False))
        if self.embedding_alg == "non-assortative":
            L_eigvals = L_eigvals ** 2

        # calculate bounds
        L_top = L_eigvals[0]
        X_top = X_eigvals[0]
        amin = (L_eigvals[n_clusters - 1] - L_eigvals[n_clusters]) / X_top ** 2
        if n_cov > n_clusters:
            amax = L_top / (X_eigvals[n_clusters - 1] ** 2 - X_eigvals[n_clusters] ** 2)
        else:
            amax = L_top / X_eigvals[n_cov - 1] ** 2

        if self.alpha == -1:
            # just use the ratio of the leading eigenvalues for the
            # tuning parameter, or the closest value in its possible range.
            alpha = np.float(L_top / X_top)
            if amin <= alpha <= amax:
                return alpha
            elif alpha < amin:
                return amin
            elif alpha > amax:
                return amax

        # run kmeans clustering and set alpha to the value
        # which minimizes clustering intertia
        alpha_range = np.linspace(amin, amax, num=self.tuning_runs)
        inertia_trials = (
            delayed(_cluster)(alpha, LL=self._LL, XXt=self._XXt, n_clusters=n_clusters)
            for alpha in alpha_range
        )
        inertias = dict(
            Parallel(n_jobs=self.n_jobs, verbose=self.verbose)(inertia_trials)
        )
        alpha = min(inertias, key=inertias.get)
        print(f"Best inertia at alpha={alpha:5f}: {inertias[alpha]:5f}")

        return alpha


def _cluster(alpha, LL, XXt, *, n_clusters):
    latents = _embed(alpha, LL=LL, XXt=XXt, n_clusters=n_clusters)
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(latents)
    return alpha, kmeans.inertia_


def _embed(alpha, LL, XXt, *, n_clusters):
    L_ = (LL + alpha * (XXt)).astype(float)
    _, vecs = eigsh(L_, k=n_clusters)

    # descending order
    vecs = np.flip(vecs, axis=1)

    return vecs
