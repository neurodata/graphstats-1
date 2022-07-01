# Copyright (c) Microsoft Corporation and contributors.
# Licensed under the MIT License.

import random
import unittest

import numpy as np
from beartype.roar import BeartypeCallHintParamViolation

from graspologic.align import SignFlips
from graspologic.embed import AdjacencySpectralEmbed
from graspologic.match import GraphMatch as GMP
from graspologic.match import graph_match
from graspologic.simulations import er_np, sbm_corr

np.random.seed(1)

# adjacency matrices from QAPLIB instance chr12c
# QAP problem is minimized with objective function value 11156
A = [
    [0, 90, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [90, 0, 0, 23, 0, 0, 0, 0, 0, 0, 0, 0],
    [10, 0, 0, 0, 43, 0, 0, 0, 0, 0, 0, 0],
    [0, 23, 0, 0, 0, 88, 0, 0, 0, 0, 0, 0],
    [0, 0, 43, 0, 0, 0, 26, 0, 0, 0, 0, 0],
    [0, 0, 0, 88, 0, 0, 0, 16, 0, 0, 0, 0],
    [0, 0, 0, 0, 26, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 16, 0, 0, 0, 96, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 29, 0],
    [0, 0, 0, 0, 0, 0, 0, 96, 0, 0, 0, 37],
    [0, 0, 0, 0, 0, 0, 0, 0, 29, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 37, 0, 0],
]
B = [
    [0, 36, 54, 26, 59, 72, 9, 34, 79, 17, 46, 95],
    [36, 0, 73, 35, 90, 58, 30, 78, 35, 44, 79, 36],
    [54, 73, 0, 21, 10, 97, 58, 66, 69, 61, 54, 63],
    [26, 35, 21, 0, 93, 12, 46, 40, 37, 48, 68, 85],
    [59, 90, 10, 93, 0, 64, 5, 29, 76, 16, 5, 76],
    [72, 58, 97, 12, 64, 0, 96, 55, 38, 54, 0, 34],
    [9, 30, 58, 46, 5, 96, 0, 83, 35, 11, 56, 37],
    [34, 78, 66, 40, 29, 55, 83, 0, 44, 12, 15, 80],
    [79, 35, 69, 37, 76, 38, 35, 44, 0, 64, 39, 33],
    [17, 44, 61, 48, 16, 54, 11, 12, 64, 0, 70, 86],
    [46, 79, 54, 68, 5, 0, 56, 15, 39, 70, 0, 18],
    [95, 36, 63, 85, 76, 34, 37, 80, 33, 86, 18, 0],
]
A, B = np.array(A), np.array(B)


class TestGraphMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # cls.A = A
        # cls.B = B
        cls.barycenter = GMP(gmp=False)
        cls.rand = GMP(n_init=100, init="rand", gmp=False)
        cls.barygm = GMP(gmp=True)

    def test_SGM_inputs(self):
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, n_init=-1.5)
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, init="not correct string")
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, max_iter=-1.5)
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, shuffle_input="hey")
        with self.assertRaises(ValueError):
            graph_match(A, B, tol=-1)
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, maximize="hey")
        with self.assertRaises(BeartypeCallHintParamViolation):
            graph_match(A, B, padding="hey")
        with self.assertRaises(ValueError):
            # A, B need to be square
            graph_match(
                np.random.random((3, 4)),
                np.random.random((3, 4)),
            )
        with self.assertRaises(ValueError):
            # BA, AB need to match A, B on certain dims
            graph_match(
                np.random.random((4, 4)),
                np.random.random((4, 4)),
                np.random.random((3, 3)),
                np.random.random((3, 3)),
            )
        with self.assertRaises(ValueError):
            # can't have more seeds than nodes
            graph_match(
                np.identity(3), np.identity(3), partial_match=np.full((5, 2), 1)
            )
        with self.assertRaises(ValueError):
            # can't have seeds that are smaller than 0
            graph_match(
                np.identity(3), np.identity(3), partial_match=np.full((2, 2), -1)
            )
        with self.assertRaises(ValueError):
            # size of similarity must fit with A, B
            graph_match(np.identity(3), np.identity(3), S=np.identity(4))

    def test_barycenter_SGM(self):
        # minimize such that we achieve some number close to the optimum,
        # though strictly greater than or equal
        # results vary due to random shuffle within GraphMatch

        n = A.shape[0]
        pi = np.array([7, 5, 1, 3, 10, 4, 8, 6, 9, 11, 2, 12]) - [1] * n
        seeds1 = [4, 8, 10]
        seeds2 = [pi[z] for z in seeds1]
        partial_match = np.column_stack((seeds1, seeds2))
        _, _, score, _ = graph_match(A, B, partial_match=partial_match, maximize=False)
        self.assertTrue(11156 <= score < 21000)

        seeds1 = np.sort(random.sample(list(range(n)), n - 1))
        seeds2 = [pi[z] for z in seeds1]
        partial_match = np.column_stack((seeds1, seeds2))
        _, _, score, _ = graph_match(A, B, partial_match=partial_match, maximize=False)
        self.assertEqual(11156, score)

        seeds1 = np.array(range(n))
        seeds2 = pi
        partial_match = np.column_stack((seeds1, seeds2))
        _, indices_B, score, _ = graph_match(
            A, B, partial_match=partial_match, maximize=False
        )
        np.testing.assert_array_equal(indices_B, pi)
        self.assertTrue(11156, score)

        seeds1 = np.random.permutation(n)
        seeds2 = [pi[z] for z in seeds1]
        partial_match = np.column_stack((seeds1, seeds2))
        _, indices_B, score, _ = graph_match(
            A, B, partial_match=partial_match, maximize=False
        )
        np.testing.assert_array_equal(indices_B, pi)
        self.assertTrue(11156, score)

    def test_rand_SGM(self):
        _, _, score, _ = graph_match(
            A, B, n_init=50, maximize=False, init_perturbation=0.5, rng=888
        )
        self.assertTrue(11156 <= score < 13500)

        n = A.shape[0]
        pi = np.array([7, 5, 1, 3, 10, 4, 8, 6, 9, 11, 2, 12]) - [1] * n
        seeds1 = [4, 8, 10]
        seeds2 = [pi[z] for z in seeds1]
        partial_match = np.column_stack((seeds1, seeds2))
        _, _, score, _ = graph_match(
            A,
            B,
            partial_match=partial_match,
            maximize=False,
            init_perturbation=0.5,
            n_init=50,
            rng=888,
        )
        self.assertTrue(11156 <= score < 12500)

    def test_parallel(self):
        gmp = GMP(gmp=False, n_init=2, n_jobs=2)
        gmp.fit(A, B)
        score = gmp.score_
        self.assertTrue(11156 <= score < 13500)

    def test_padding(self):
        n = 50
        p = 0.4

        G1 = er_np(n=n, p=p)
        G2 = G1[:-2, :-2]  # remove two nodes
        gmp_adopted = GMP(padding="adopted")
        res = gmp_adopted.fit(G1, G2)

        self.assertTrue(0.95 <= (sum(res.perm_inds_ == np.arange(n)) / n))

    def test_custom_init(self):
        n = len(A)
        pi = np.array([7, 5, 1, 3, 10, 4, 8, 6, 9, 11, 2, 12]) - [1] * n
        custom_init = np.eye(n)
        custom_init = custom_init[pi]

        gm = GMP(n_init=1, init=custom_init, max_iter=30, shuffle_input=True, gmp=False)
        gm.fit(A, B)

        self.assertTrue((gm.perm_inds_ == pi).all())
        self.assertEqual(gm.score_, 11156)
        # we had thought about doing the test
        # `assert gm.n_iter_ == 1`
        # but note that GM doesn't necessarily converge in 1 iteration here
        # this is because when we start from the optimal permutation matrix, we do
        # not start from the optimal over our convex relaxation (the doubly stochastics)
        # but we do indeed recover the correct permutation after a small number of
        # iterations

    def test_custom_init_seeds(self):
        n = len(A)
        pi_original = np.array([7, 5, 1, 3, 10, 4, 8, 6, 9, 11, 2, 12]) - 1
        pi = np.array([5, 1, 3, 10, 4, 8, 6, 9, 11, 2, 12]) - 1

        pi[pi > 6] -= 1

        # use seed 0 in A to 7 in B
        seeds_A = [0]
        seeds_B = [6]
        custom_init = np.eye(n - 1)
        custom_init = custom_init[pi]

        gm = GMP(n_init=1, init=custom_init, max_iter=30, shuffle_input=True, gmp=False)
        gm.fit(A, B, seeds_A=seeds_A, seeds_B=seeds_B)

        self.assertTrue((gm.perm_inds_ == pi_original).all())
        self.assertEqual(gm.score_, 11156)

    def test_sim(self):
        n = 150
        rho = 0.9
        n_per_block = int(n / 3)
        n_blocks = 3
        block_members = np.array(n_blocks * [n_per_block])
        block_probs = np.array(
            [[0.2, 0.01, 0.01], [0.01, 0.1, 0.01], [0.01, 0.01, 0.2]]
        )
        directed = False
        loops = False
        A1, A2 = sbm_corr(
            block_members, block_probs, rho, directed=directed, loops=loops
        )
        ase = AdjacencySpectralEmbed(n_components=3, algorithm="truncated")
        x1 = ase.fit_transform(A1)
        x2 = ase.fit_transform(A2)
        xh1 = SignFlips().fit_transform(x1, x2)
        S = xh1 @ x2.T
        res = self.barygm.fit(A1, A2, S=S)

        self.assertTrue(0.7 <= (sum(res.perm_inds_ == np.arange(n)) / n))

        A1 = A1[:-1, :-1]
        xh1 = xh1[:-1, :]
        S = xh1 @ x2.T

        res = self.barygm.fit(A1, A2, S=S)

        self.assertTrue(0.6 <= (sum(res.perm_inds_ == np.arange(n)) / n))
