import pytest
import numpy as np
from graspy.match import FastApproximateQAP as FAQ


class TestMatch:
    @classmethod
    def setup_class(cls):
        cls.barycenter = FAQ()
        cls.rand = FAQ(n_init=100, init_method="rand")

    def test_FAQ_inputs(self):
        with pytest.raises(TypeError):
            FAQ(n_init=-1.5)
        with pytest.raises(ValueError):
            FAQ(init_method="random")
        with pytest.raises(TypeError):
            FAQ(max_iter=-1.5)
        with pytest.raises(TypeError):
            FAQ(shuffle_input="hey")
        with pytest.raises(TypeError):
            FAQ(eps=-1)

    def test_barycenter(self):
        A = np.array(
            (
                [0, 17, 5, 12, 0, 11, 0, 6, 17, 18, 6, 18, 2, 15, 6, 9, 18, 12, 2, 4],
                [
                    16,
                    0,
                    12,
                    17,
                    16,
                    15,
                    14,
                    12,
                    17,
                    19,
                    16,
                    15,
                    8,
                    17,
                    8,
                    9,
                    8,
                    14,
                    7,
                    5,
                ],
                [5, 12, 0, 3, 3, 0, 9, 13, 0, 2, 9, 13, 2, 7, 1, 7, 19, 0, 2, 19],
                [11, 17, 3, 0, 6, 1, 10, 19, 6, 15, 4, 0, 19, 19, 4, 1, 9, 9, 3, 6],
                [0, 16, 2, 6, 0, 0, 11, 9, 18, 0, 17, 9, 9, 16, 14, 12, 10, 14, 9, 1],
                [11, 15, 0, 1, 0, 0, 14, 7, 19, 2, 15, 11, 14, 14, 4, 14, 7, 14, 6, 17],
                [0, 14, 8, 9, 11, 14, 0, 19, 9, 11, 17, 0, 14, 6, 16, 14, 3, 8, 2, 15],
                [5, 12, 14, 19, 10, 8, 19, 0, 0, 2, 4, 19, 6, 6, 8, 15, 6, 18, 15, 4],
                [16, 17, 0, 6, 18, 19, 10, 0, 0, 3, 10, 8, 12, 4, 7, 5, 0, 19, 4, 7],
                [18, 19, 3, 15, 0, 2, 12, 1, 3, 0, 7, 12, 10, 7, 7, 15, 14, 12, 15, 17],
                [7, 16, 10, 4, 17, 15, 17, 5, 10, 8, 0, 13, 8, 1, 12, 8, 2, 5, 15, 10],
                [18, 15, 12, 0, 10, 12, 0, 18, 8, 12, 13, 0, 18, 8, 1, 8, 5, 4, 18, 1],
                [2, 8, 2, 19, 10, 13, 13, 7, 11, 10, 8, 18, 0, 1, 15, 8, 10, 5, 9, 7],
                [15, 17, 7, 18, 16, 13, 7, 7, 4, 8, 1, 8, 2, 0, 13, 16, 1, 1, 9, 4],
                [7, 8, 2, 5, 13, 5, 16, 8, 6, 8, 11, 2, 15, 13, 0, 1, 13, 1, 13, 11],
                [9, 9, 6, 2, 11, 13, 13, 15, 5, 15, 8, 8, 8, 16, 1, 0, 4, 6, 5, 2],
                [17, 8, 18, 8, 9, 6, 3, 6, 0, 13, 3, 6, 9, 1, 13, 3, 0, 6, 3, 4],
                [11, 13, 0, 8, 13, 13, 8, 17, 19, 11, 4, 4, 4, 2, 0, 6, 6, 0, 8, 15],
                [2, 7, 3, 3, 9, 6, 1, 15, 4, 15, 14, 17, 9, 9, 13, 4, 2, 7, 0, 13],
                [4, 4, 18, 5, 1, 17, 14, 4, 5, 17, 9, 1, 5, 4, 11, 1, 4, 14, 13, 0],
            )
        )
        B = np.array(
            (
                [0, 6, 12, 9, 19, 9, 18, 12, 6, 4, 12, 4, 15, 7, 12, 10, 4, 9, 15, 13],
                [6, 0, 9, 5, 6, 7, 8, 9, 5, 3, 6, 7, 11, 5, 11, 10, 11, 8, 11, 13],
                [
                    12,
                    9,
                    0,
                    14,
                    14,
                    19,
                    11,
                    8,
                    18,
                    14,
                    10,
                    9,
                    15,
                    12,
                    15,
                    12,
                    3,
                    18,
                    14,
                    3,
                ],
                [
                    9,
                    5,
                    14,
                    0,
                    12,
                    15,
                    10,
                    3,
                    12,
                    7,
                    13,
                    18,
                    1,
                    3,
                    13,
                    15,
                    11,
                    11,
                    14,
                    12,
                ],
                [19, 6, 14, 12, 0, 19, 9, 10, 4, 18, 5, 10, 10, 6, 8, 9, 10, 8, 10, 16],
                [9, 7, 19, 15, 19, 0, 8, 11, 1, 15, 7, 9, 8, 8, 13, 8, 12, 8, 12, 5],
                [18, 8, 11, 10, 9, 8, 0, 3, 10, 9, 5, 18, 8, 12, 6, 8, 14, 11, 15, 7],
                [12, 9, 8, 3, 10, 11, 3, 0, 18, 15, 13, 3, 12, 12, 11, 7, 12, 4, 7, 13],
                [
                    6,
                    5,
                    18,
                    12,
                    4,
                    1,
                    10,
                    18,
                    0,
                    14,
                    10,
                    11,
                    9,
                    13,
                    12,
                    13,
                    19,
                    1,
                    13,
                    12,
                ],
                [4, 3, 14, 7, 18, 15, 9, 15, 14, 0, 11, 9, 10, 11, 11, 7, 8, 9, 7, 5],
                [
                    12,
                    6,
                    10,
                    13,
                    5,
                    7,
                    5,
                    13,
                    10,
                    11,
                    0,
                    8,
                    11,
                    16,
                    9,
                    11,
                    14,
                    13,
                    7,
                    10,
                ],
                [4, 7, 9, 18, 10, 9, 18, 3, 11, 9, 8, 0, 4, 11, 15, 11, 12, 13, 4, 16],
                [
                    15,
                    11,
                    15,
                    1,
                    10,
                    8,
                    8,
                    12,
                    9,
                    10,
                    11,
                    4,
                    0,
                    15,
                    7,
                    11,
                    10,
                    13,
                    10,
                    12,
                ],
                [
                    7,
                    5,
                    12,
                    3,
                    6,
                    8,
                    12,
                    12,
                    13,
                    11,
                    16,
                    11,
                    15,
                    0,
                    8,
                    6,
                    15,
                    15,
                    10,
                    13,
                ],
                [12, 11, 15, 13, 8, 13, 6, 11, 12, 11, 9, 15, 7, 8, 0, 15, 8, 17, 8, 9],
                [
                    10,
                    10,
                    12,
                    15,
                    9,
                    8,
                    8,
                    7,
                    13,
                    7,
                    11,
                    11,
                    11,
                    6,
                    15,
                    0,
                    14,
                    12,
                    13,
                    15,
                ],
                [
                    4,
                    11,
                    3,
                    11,
                    10,
                    12,
                    14,
                    12,
                    19,
                    8,
                    14,
                    12,
                    10,
                    15,
                    8,
                    14,
                    0,
                    12,
                    14,
                    13,
                ],
                [9, 8, 18, 11, 8, 8, 11, 4, 1, 9, 13, 13, 13, 15, 17, 12, 12, 0, 11, 7],
                [
                    15,
                    11,
                    14,
                    14,
                    10,
                    12,
                    15,
                    7,
                    13,
                    7,
                    7,
                    4,
                    10,
                    10,
                    8,
                    13,
                    14,
                    11,
                    0,
                    8,
                ],
                [
                    13,
                    13,
                    3,
                    12,
                    16,
                    5,
                    7,
                    13,
                    12,
                    5,
                    10,
                    16,
                    12,
                    13,
                    9,
                    15,
                    13,
                    7,
                    8,
                    0,
                ],
            )
        )
        score = self.barycenter.fit(A, B).score_
        assert score == 27076.0

    def test_rand(self):
        A = np.array(
            (
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
            )
        )
        B = np.array(
            (
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
            )
        )
        rand = FAQ(n_init=100, init_method="rand")
        score = rand.fit(A, B).score_
        assert 11156 <= score < 13500
