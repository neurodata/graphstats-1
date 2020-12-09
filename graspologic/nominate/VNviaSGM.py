import numpy as np
from ..match import GraphMatch as GMP
from sklearn.base import BaseEstimator
import itertools


class VNviaSGM(BaseEstimator):
    """
    This class implements Vertex Nomination via Seeded Graph Matching
    (VNviaSGM) with the algorithm described in [1].

    VNviaSGM is a nomination algorithm, so instead of completely matching two
    graphs `A` and `B`, it proposes a nomination list of potential matches in
    graph `B` to a vertex of interest (voi) in graph `A` with associated
    probabilities. VNviaSGM generates an initial induced subgraph about the
    voi to determine which seeds are close enough to be used.
    All the seeds that are close enough are then used to generate subgraphs in
    both A and B. These subgraphs are matched using the seeded graph matching
    algorithm (SGM), and a nomination list is returned.

    Parameters
    ----------
    order_voi_subgraph: int, positive (default = 1)
        Order used to create induced subgraph on `A` about voi.
        This induced subgraph will be used to determine what seeds are used
        when the SGM algorithm is called. If no seeds are in this subgraph
        about voi, then VNviaSGM will return None.

    order_seeds_subgraph: int, positive (default = 1)
        Order used to  create induced subgraphs on `A`
        and `B`. These subgraphs are centered about the seeds that were determined
        by the subgraph generated by `order_voi_subgraph`. These two subgraphs will
        be passed into the SGM algorithm.

    n_init: int, positive (default = 100)
        Number of restarts for soft seeded graph matching algorithm. Increasing the
        number of restarts will make the probabilites returned more precise.

    Attributes
    ----------
    n_seeds: int
        Number of seeds passed in `seedsA` that occured in the induced subgraph about `voi`

    nomination_list: 2d-array
        An array containing vertex nominations in the form nomination list = [[j, p_val],...]
        where p_val is the probability that the voi matches to node j in graph B (sorted by
        descending probability)


    References
    ----------
    .. [1] Patsolic, HG, Park, Y, Lyzinski, V, Priebe, CE. Vertex nomination via seeded graph matching. Stat Anal Data
        Min: The ASA Data Sci Journal. 2020; 13: 229– 244. https://doi.org/10.1002/sam.11454



    """

    def __init__(self, order_voi_subgraph=1, order_seeds_subgraph=1, n_init=100):
        if isinstance(order_voi_subgraph, int) and order_voi_subgraph > 0:
            self.order_voi_subgraph = order_voi_subgraph
        else:
            msg = "order_voi_subgraph must be an integer > 0"
            raise ValueError(msg)
        if isinstance(order_seeds_subgraph, int) and order_seeds_subgraph > 0:
            self.order_seeds_subgraph = order_seeds_subgraph
        else:
            msg = "order_seeds_subgraph must be an integer > 0"
            raise ValueError(msg)
        if isinstance(n_init, int) and n_init > 0:
            self.n_init = n_init
        else:
            msg = "R must be an integer > 0"
            raise ValueError(msg)

    def fit(self, A, B, voi, seeds=[]):
        """
        Fits the model to two graphs.

        Parameters
        ----------
        A: 2d-array, square
            Adjacency matrix of `A`, the graph where voi is known

        B: 2d-array, square
            Adjacency matrix of `B`, the graph where voi is not known

        voi: int
            Vertex of interest (voi)

        seeds: list
            List of length two `[seedsA, seedsB]` where first element is
            the seeds associated with adjacency matrix A
            and the second element the adjacency matrix associated with B, note
            `len(seedsA)==len(seedsB)`. The elements of `seedsA` and `seedsB` are
            vertices which are known to be matched, that is, `seedsA[i]` is matched
            to vertex `seedsB[i]`.

        Returns
        -------
        self: A reference to self
        """
        if A is None or B is None:
            msg = "Adjacency matrices must be passed"
            raise ValueError(msg)
        elif A.ndim != 2 or B.ndim != 2:
            msg = "Adjacency matrix entries must be two-dimensional"
            raise ValueError(msg)
        elif A.shape[0] != A.shape[1] or B.shape[0] != B.shape[1]:
            msg = "Adjacency matrix entries must be square"
            raise ValueError(msg)

        if len(seeds) == 0:
            print("Must include at least one seed to produce nomination list")
            return None
        if len(seeds) != 2:
            msg = "List must be length two, with first element containing seeds \
                  of A and the second containing seeds of B"
            raise ValueError(msg)

        seedsA = seeds[0]
        seedsB = seeds[1]

        if len(seedsA) != len(seedsB):
            msg = "Must have the same number of seeds for each adjacency matrix"
            raise ValueError(msg)
        if len(seedsA) == 0:
            msg = "Must include at least one seed to produce nomination list"
            raise ValueError(msg)

        voi = np.reshape(np.array(voi), (1,))

        # get vertex reordering for Ax
        # in the form (seedsA, voi, rest in order)
        nsx1 = np.setdiff1d(np.arange(A.shape[0]), np.concatenate((seedsA, voi)))
        a_reord = np.concatenate((seedsA, voi, nsx1))

        # get reordering for B in the form (seedsB, rest in numerical order)
        nsx2 = np.setdiff1d(np.arange(B.shape[0]), seedsB)
        b_reord = np.concatenate((seedsB, nsx2))

        # Reorder the two graphs with our new vertices order
        AA = A[np.ix_(a_reord, a_reord)]
        BB = B[np.ix_(b_reord, b_reord)]

        # Record where the new seeds and voi locations are
        # in our re-ordered graphs
        seeds_reord = np.arange(len(seedsA))
        voi_reord = len(seedsA)

        # Determine what seeds are within a specified subgraph
        # given by `self.order_voi_subgraph`. If there are no
        # seeds in this subgraph, print a message and return None
        subgraph_AA = np.array(
            _get_induced_subgraph_list(
                AA, self.order_voi_subgraph, voi_reord, mindist=1
            )
        )
        close_seeds = np.intersect1d(subgraph_AA, seeds_reord)

        if len(close_seeds) <= 0:
            print(
                "Voi {} was not a member of the induced subgraph A[{}]".format(
                    voi, seedsA
                )
            )
            return None

        voi_reord = np.reshape(np.array(voi_reord), (1,))

        # Generate the two induced subgraphs that will be used by the matching
        # algorithm using the seeds that we identified in the previous step.
        verts_A = np.array(
            _get_induced_subgraph_list(
                AA, self.order_seeds_subgraph, list(close_seeds), mindist=0
            )
        )
        verts_B = np.array(
            _get_induced_subgraph_list(
                BB, self.order_seeds_subgraph, list(close_seeds), mindist=0
            )
        )

        # Determine the final reordering for the graphs that include only
        # the vertices found by the induced subgraphs in the previous step
        # For graph A, its of the form (close_seeds, voi, rest in verts_A
        # in num order). For graph B its of the form (close_seeds, rest in
        # verts_B in num order)
        foo = np.concatenate((close_seeds, voi_reord))
        ind1 = np.concatenate((close_seeds, voi_reord, np.setdiff1d(verts_A, foo)))
        ind2 = np.concatenate((close_seeds, np.setdiff1d(verts_B, close_seeds)))

        # Generate adjacency matrices for the ordering found in the prev step
        AA_fin = AA[np.ix_(ind1, ind1)]
        BB_fin = BB[np.ix_(ind2, ind2)]

        # Call the SGM algorithm using random initialization and naive padding
        # Run the alg on the adjacency matrices we found in the prev step
        seeds_fin = list(range(len(close_seeds)))
        sgm = GMP(n_init=self.n_init, shuffle_input=False, init="rand", padding="naive")
        corr = sgm.fit_predict(AA_fin, BB_fin, seeds_A=seeds_fin, seeds_B=seeds_fin)
        P_outp = sgm.probability_matrix_

        # Get the original vertices names in the B graph to make the nom list
        b_inds = b_reord[ind2]

        # Record the number of seeds used because this may differ from the number
        # of seeds passed. See the step where close_seeds was computed for an
        # explanation
        self.n_seeds = len(close_seeds)

        # Generate the nomination list. Note, the probability matrix does not
        # include the seeds, so we must remove them from b_inds. Return a list
        # sorted so it returns the vertex with the highest probability first.
        nomination_list = list(zip(b_inds[self.n_seeds :], P_outp[0]))
        nomination_list.sort(key=lambda x: x[1], reverse=True)
        self.nomination_list = np.array(nomination_list)

        return self

    def fit_predict(self, A, B, voi, seeds=[]):
        """
        Fits model to two adjacency matrices and returns nomination list

        Parameters
        ----------
        A: 2d-array, square
            Adjacency matrix of `A`, the graph where voi is known

        B: 2d-array, square
            Adjacency matrix of `B`, the graph where voi is not known

        voi: int
            Vertex of interest (voi)

        seeds: list
            List of length two `[seedsA, seedsB]` where first element is
            the seeds associated with adjacency matrix A
            and the second element the adjacency matrix associated with B, note
            `len(seedsA)==len(seedsB)` The elements of `seedsA` and `seedsB` are
            vertices which are known to be matched, that is, `seedsA[i]` is matched
            to vertex `seedsB[i]`.

        Returns
        -------
        nomination_list : 2d-array
            The nomination array
        """
        retval = self.fit(A, B, voi, seeds)

        # It is possible that the algorithm stops early and returns none
        # if the task is impossible. Note, this does not mean that the input
        # arguments were erroneous.
        if retval is None:
            return None

        return self.nomination_list


def _get_induced_subgraph(graph_adj_matrix, order, node, mindist=1):
    """
    Generates a vertex list for the induced subgraph about a node with
    max (order_ and min distance parameters.

    Parameters
    ----------
    graph_adj_matrix: 2-d array
        Adjacency matrix of interest.

    order: int
        Distance to create the induced subgraph with. Max distance away from
        the node to include in subgraph.

    node: int
        The vertex to center the induced subgraph about.

    mindist: int (default = 1)
        The minimum distance away from the node to include in the subgraph.

    Returns
    -------
    induced_subgraph : list
        The list containing all the vertices in the induced subgraph.
    """
    # Note all nodes are zero based in this implementation, i.e the first node is 0
    dists = [[node]]
    dists_conglom = [node]
    for ii in range(1, order + 1):
        clst = []
        for nn in dists[-1]:
            clst.extend(list(np.where(graph_adj_matrix[nn] >= 1)[0]))
        clst = np.array(list(set(clst)))

        cn_proc = np.setdiff1d(clst, dists_conglom)

        dists.append(cn_proc)

        dists_conglom.extend(cn_proc)
        dists_conglom = list(set(dists_conglom))

    ress = itertools.chain(*dists[mindist : order + 1])

    return np.array(list(set(ress)))


def _get_induced_subgraph_list(graph_adj_matrix, order, node, mindist=1):
    """
    Generates a vertex list for the induced subgraph about a node with
    max and min distance parameters.

    Parameters
    ----------
    graph_adj_matrix: 2-d array
        Adjacency matrix of interest.

    order: int
        Distance to create the induce subgraph with. Max distance away from
        the node to include in subgraph.

    node: int or list
        The list of vertices to center the induced subgraph about.

    mindist: int (default = 1)
        The minimum distance away from the node to include in the subgraph.

    Returns
    -------
    induced_subgraph : list
        The list containing all the vertices in the induced subgraph.
    """
    if type(node) == list:
        total_res = []
        for nn in node:
            ego_res = _get_induced_subgraph(
                graph_adj_matrix, order, nn, mindist=mindist
            )
            total_res.extend(ego_res)
        return list(set(total_res))
    else:
        return _get_induced_subgraph(graph_adj_matrix, order, node)
