import numpy as np

class KalmanFilter:
    def __init__(self, dt=1.0, u_x=1.0, u_y=1.0, std_acc=1.0, x_std_meas=0.1, y_std_meas=0.1):
        """
        Initialize Kalman Filter for tracking position and velocity.
        
        Args:
            dt: Time step
            u_x: Initial x velocity uncertainty
            u_y: Initial y velocity uncertainty
            std_acc: Process noise magnitude (acceleration standard deviation)
            x_std_meas: Standard deviation of x measurement noise
            y_std_meas: Standard deviation of y measurement noise
        """
        self.dt = dt

        # Initial State (x, y, dx, dy)
        self.x = np.zeros((4, 1))

        # State Transition Matrix (A)
        # x_new = x + dx*dt
        # y_new = y + dy*dt
        # dx_new = dx
        # dy_new = dy
        self.A = np.array([
            [1, 0, self.dt, 0],
            [0, 1, 0, self.dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        # Measurement Matrix (H)
        # We measure only x and y
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

        # Measurement Noise Covariance (R)
        self.R = np.array([
            [x_std_meas**2, 0],
            [0, y_std_meas**2]
        ])

        # Process Noise Covariance (Q)
        # Assumes acceleration is the process noise
        self.Q = np.array([
            [(self.dt**4)/4, 0, (self.dt**3)/2, 0],
            [0, (self.dt**4)/4, 0, (self.dt**3)/2],
            [(self.dt**3)/2, 0, self.dt**2, 0],
            [0, (self.dt**3)/2, 0, self.dt**2]
        ]) * std_acc**2

        # Error Covariance Matrix (P)
        self.P = np.eye(self.A.shape[0])

    def predict(self):
        """Predict the next state."""
        self.x = np.dot(self.A, self.x)
        self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q
        return self.x[:2]

    def update(self, z):
        """
        Update the state with a new measurement z = [x, y].
        
        Args:
            z: Measurement vector (x, y)
        """
        # Measurement Residual
        y = z - np.dot(self.H, self.x)
        
        # Residual Covariance
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R
        
        # Optimal Kalman Gain
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        
        # Update State
        self.x = self.x + np.dot(K, y)
        
        # Update Error Covariance
        I = np.eye(self.H.shape[1])
        self.P = np.dot((I - np.dot(K, self.H)), self.P)
        
        return self.x[:2]

    def get_state(self):
        """Return the current state (x, y, dx, dy)."""
        return self.x
