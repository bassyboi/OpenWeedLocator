import numpy as np

def compute_ground_homography(fx, fy, cx, cy, tilt_deg, cam_height):
    """
    Compute a 3×3 homography that maps ground-plane (Z=0) points into image pixels,
    given camera intrinsics and a pitch of `tilt_deg` (around X axis) and camera height.
    """
    # Intrinsic matrix
    K = np.array([[fx,   0, cx],
                  [  0, fy, cy],
                  [  0,   0,  1]], dtype=np.float64)

    # Rotation around X axis by tilt_deg
    θ = np.deg2rad(tilt_deg)
    R = np.array([[1,         0,          0],
                  [0,  np.cos(θ), -np.sin(θ)],
                  [0,  np.sin(θ),  np.cos(θ)]], dtype=np.float64)

    # Translation vector: camera sits `cam_height` metres above ground plane
    T = np.array([[0], [cam_height], [0]], dtype=np.float64)

    # Homography for plane Y=0: use columns [R[:,0], R[:,2], T]
    H = K @ np.hstack((R[:, [0, 2]], T))

    # Normalize so H[2,2] == 1
    return H / H[2, 2]
