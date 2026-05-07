import numpy as np
from typing import Tuple

class PCAReducer:
    """
    Dimensionality reduction for large feature sets (e.g. microstructure/SMC clusters).
    """
    def __init__(self, variance_threshold: float = 0.95):
        self.threshold = variance_threshold
        self.components = None
        self.mean = None

    def fit(self, X: np.ndarray):
        self.mean = np.mean(X, axis=0)
        X_centered = X - self.mean
        cov = np.cov(X_centered, rowvar=False)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        
        # Sort in descending order
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Determine number of components
        total_var = np.sum(eigenvalues)
        explained_var = np.cumsum(eigenvalues) / total_var
        k = np.argmax(explained_var >= self.threshold) + 1
        
        self.components = eigenvectors[:, :k]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean) @ self.components

class OLSRegression:
    """
    Predictive modeling using Ordinary Least Squares.
    """
    def __init__(self):
        self.beta = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        # Adding intercept
        X_design = np.column_stack([np.ones(X.shape[0]), X])
        self.beta = np.linalg.pinv(X_design.T @ X_design) @ X_design.T @ y
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_design = np.column_stack([np.ones(X.shape[0]), X])
        return X_design @ self.beta

class MatrixOps:
    """
    High-precision matrix operations for quant modeling.
    """
    @staticmethod
    def safe_inverse(A: np.ndarray) -> np.ndarray:
        try:
            # Prefer Cholesky if PD
            L = np.linalg.cholesky(A)
            L_inv = np.linalg.inv(L)
            return L_inv.T @ L_inv
        except np.linalg.LinAlgError:
            return np.linalg.pinv(A)

    @staticmethod
    def orthogonalize(A: np.ndarray) -> np.ndarray:
        # Gram-Schmidt
        Q, R = np.linalg.qr(A)
        return Q
