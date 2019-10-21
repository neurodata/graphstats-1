# -*- coding: utf-8 -*-
"""
Created on Sun Oct 20 19:46:01 2019

@author: jerryyao
"""

# Copyright 2019 NeuroData (http://neurodata.io)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import warnings

from .base import BaseEmbed
from ..utils import import_graph, to_laplace, is_fully_connected
from .svd import selectSVD
import numpy as np
from sklearn import preprocessing

from sklearn.cluster import KMeans
class CovariateAssistedSpectralEmbed(BaseEmbed):
    r"""
    Class for computing the laplacian spectral embedding of a graph 
    
    The laplacian spectral embedding (LSE) is a k-dimensional Euclidean representation
    of the graph based on its Laplacian matrix [1]_. It relies on an SVD to reduce 
    the dimensionality to the specified k, or if k is unspecified, can find a number
    of dimensions automatically.

    Read more in the :ref:`tutorials <embed_tutorials>`

    Parameters
    ----------
    form : {'DAD' (default), 'I-DAD', 'R-DAD'}, optional
        Specifies the type of Laplacian normalization to use.

    n_components : int or None, default = None
        Desired dimensionality of output data. If "full", 
        n_components must be <= min(X.shape). Otherwise, n_components must be
        < min(X.shape). If None, then optimal dimensions will be chosen by
        :func:`~graspy.embed.select_dimension` using ``n_elbows`` argument.

    n_elbows : int, optional, default: 2
        If ``n_components=None``, then compute the optimal embedding dimension using
        :func:`~graspy.embed.select_dimension`. Otherwise, ignored.

    algorithm : {'randomized' (default), 'full', 'truncated'}, optional
        SVD solver to use:

        - 'randomized'
            Computes randomized svd using 
            :func:`sklearn.utils.extmath.randomized_svd`
        - 'full'
            Computes full svd using :func:`scipy.linalg.svd`
        - 'truncated'
            Computes truncated svd using :func:`scipy.sparse.linalg.svds`

    n_iter : int, optional (default = 5)
        Number of iterations for randomized SVD solver. Not used by 'full' or 
        'truncated'. The default is larger than the default in randomized_svd 
        to handle sparse matrices that may have large slowly decaying spectrum.

    check_lcc : bool , optional (defult = True)
        Whether to check if input graph is connected. May result in non-optimal 
        results if the graph is unconnected. If True and input is unconnected,
        a UserWarning is thrown. Not checking for connectedness may result in 
        faster computation.

    regularizer: int, float or None, optional (default=None)
        Constant to be added to the diagonal of degree matrix. If None, average 
        node degree is added. If int or float, must be >= 0. Only used when 
        ``form`` == 'R-DAD'.

    Attributes
    ----------
    latent_left_ : array, shape (n_samples, n_components)
        Estimated left latent positions of the graph.

    latent_right_ : array, shape (n_samples, n_components), or None
        Only computed when the graph is directed, or adjacency matrix is assymetric.
        Estimated right latent positions of the graph. Otherwise, None.

    singular_values_ : array, shape (n_components)
        Singular values associated with the latent position matrices.

    See Also
    --------
    graspy.embed.selectSVD
    graspy.embed.select_dimension
    graspy.utils.to_laplace

    Notes
    -----
    The singular value decomposition: 

    .. math:: A = U \Sigma V^T

    is used to find an orthonormal basis for a matrix, which in our case is the
    Laplacian matrix of the graph. These basis vectors (in the matrices U or V) are 
    ordered according to the amount of variance they explain in the original matrix. 
    By selecting a subset of these basis vectors (through our choice of dimensionality
    reduction) we can find a lower dimensional space in which to represent the graph.

    References
    ----------
    .. [1] Sussman, D.L., Tang, M., Fishkind, D.E., Priebe, C.E.  "A
       Consistent Adjacency Spectral Embedding for Stochastic Blockmodel Graphs,"
       Journal of the American Statistical Association, Vol. 107(499), 2012
    """

    def __init__(
        self,
        form="R-DAD",
        n_components=None,
        n_elbows=2,
        algorithm="randomized",
        n_iter=50,
        check_lcc=True,
        regularizer=1,
        assortative=True,
        row_norm=False,
        n_points=100
    ):
        super().__init__(
            n_components=n_components,
            n_elbows=n_elbows,
            algorithm=algorithm,
            n_iter=n_iter,
            check_lcc=check_lcc,
        )
        self.form = form
        self.regularizer = regularizer
        self.assortative = assortative
        self.row_norm=row_norm
        self.n_points=n_points
    def fit(self, graph, covariate_matrix,y=None):
        """
        Fit LSE model to input graph

        By default, uses the Laplacian normalization of the form:

        .. math:: L = D^{-1/2} A D^{-1/2}

        Parameters
        ----------
        graph : array_like or networkx.Graph
            Input graph to embed. see graspy.utils.import_graph

        y : Ignored

        Returns
        -------
        self : returns an instance of self.
        """
        A = import_graph(graph)
        
        if self.check_lcc:
            if not is_fully_connected(A):
                msg = (
                    "Input graph is not fully connected. Results may not"
                    + "be optimal. You can compute the largest connected component by"
                    + "using ``graspy.utils.get_lcc``."
                )
                warnings.warn(msg, UserWarning)

        L_norm = to_laplace(A, form=self.form, regularizer=self.regularizer)
        [hmax,hmin]=self.get_tuning_range(L_norm,covariate_matrix,self.n_components,self.assortative)
        res=self.getCascClusters(L_norm, covariate_matrix,hmin,hmax, self.n_components,self.n_points, self.row_norm, self.assortative)
        
        return res
    def get_tuning_range(self,graphMatrix, covariates, nBlocks,assortative):
        nCov = covariates.shape[1]
        U, D, V = selectSVD(covariates,n_components=covariates.shape[1],n_elbows=self.n_elbows,algorithm='full')    
        min_tmp = np.min([nCov,nBlocks])
        singValCov = D[0:min_tmp]
        if assortative:
            u1,d1,v1 = selectSVD(graphMatrix,n_components=graphMatrix.shape[0],n_elbows=self.n_elbows,algorithm='full',)
            tmp1 = nBlocks + 1
            eigenValGraph = d1[0:tmp1]
            if nCov > nBlocks:
                hmax = eigenValGraph[0]/(singValCov[nBlocks-1]**2 - singValCov[nBlocks]**2) 
            else:
                hmax = eigenValGraph[0]/singValCov[nCov-1]**2 
            hmin = (eigenValGraph[nBlocks-1] - eigenValGraph[nBlocks])/singValCov[0]**2
        else:
            u1,d1,v1 = selectSVD(graphMatrix,n_components=graphMatrix.shape[0],n_elbows=self.n_elbows,algorithm='full',)
            tmp1 = nBlocks + 1
            eigenValGraph = d1[0:tmp1]**2
            if nCov > nBlocks :
                hmax = eigenValGraph[0]/(singValCov[nBlocks-1]**2 - singValCov[nBlocks]**2) 
            else:
                hmax = eigenValGraph[0]/singValCov[nCov-1]**2 
            hmin = (eigenValGraph[nBlocks-1] - eigenValGraph[nBlocks])/singValCov[0]**2
        return [hmax,hmin]
   
    def getCascClusters(self,graphMat, covariates,hmin,hmax, nBlocks,nPoints, rowNorm, assortative):
    	
    	hTuningSeq = np.linspace(hmax,hmin,nPoints)
    	wcssVec = []
    	gapVec = []
    	orthoX = []
    	orthoL = []
        
    	for i in range(nPoints):
    		cascResults = self.getCascResults(graphMat, covariates, hTuningSeq[i],nBlocks, rowNorm, assortative)
    		orthoL.append(cascResults['orthoL'])
    		orthoX.append(cascResults['orthoX'])
    		wcssVec.append(cascResults['wcss'])
    		gapVec.append(cascResults['gapVec'])
          
    	hOpt = hTuningSeq[wcssVec.index(min(wcssVec))]
    	hOptResults = self.getCascResults(graphMat, covariates, hOpt, nBlocks, rowNorm,assortative)
    	return {'cluster':hOptResults['cluster'],'h':hOpt,'wcss':hOptResults['wcss'],'eigenGap':hOptResults['gapVec'],'cascSvd':hOptResults['cascSvd']}
    
    def getOrtho(self,graphMat, covariates, cascSvdEVec, cascSvdEVal,h, nBlocks):
    	orthoL=cascSvdEVec[:, (nBlocks-1)].transpose().dot(graphMat).dot(cascSvdEVec[:,(nBlocks-1)]).transpose()/cascSvdEVal[(nBlocks-1)]
    	orthoX=h*(cascSvdEVec[:, (nBlocks-1)].transpose().dot(covariates).dot(covariates.transpose()).dot(cascSvdEVec[:,(nBlocks-1)])/cascSvdEVal[(nBlocks-1)])
    	return [orthoL/(orthoL + orthoX),orthoX/(orthoL + orthoX)]
    
    
    def getCascSvd(self,graphMat, covariates, hTuningParam, nBlocks, assortative):
        if assortative:
    	
            New_laplacian=(graphMat + np.dot(hTuningParam * covariates,covariates.transpose()))
    			
        else:
            
            New_laplacian=((np.dot(graphMat,graphMat)) + np.dot(hTuningParam * covariates,covariates.transpose()))
            
        u2,d2,v2 = selectSVD(New_laplacian,n_components=New_laplacian.shape[0],n_elbows=self.n_elbows,algorithm='full')	
        
        eVec = u2[:, 0:nBlocks]
        eVal = d2[0:(nBlocks+1)]
    
        return {'eVec':eVec,'eVal':eVal}
    def getCascResults(self,graphMat, covariates, hTuningParam,nBlocks, rowNorm,assortative):
    	cascSvd = self.getCascSvd(graphMat, covariates, hTuningParam, nBlocks, assortative)
    	ortho = self.getOrtho(graphMat, covariates, cascSvd['eVec'], cascSvd['eVal'],hTuningParam, nBlocks)
    	if rowNorm:
    		cascSvd_tmp = cascSvd['eVec']/np.sqrt(sum(cascSvd['eVec']**2))
    	else:
    		cascSvd_tmp = cascSvd['eVec']
    	kmeansResults=KMeans(n_clusters=nBlocks).fit(cascSvd_tmp)
    	return {'orthoL':ortho[0],'orthoX':ortho[1],'wcss':kmeansResults.inertia_,'cluster':kmeansResults.labels_,'gapVec':cascSvd['eVal'][nBlocks-1]-cascSvd['eVal'][nBlocks],'cascSvd':cascSvd_tmp}
        
    