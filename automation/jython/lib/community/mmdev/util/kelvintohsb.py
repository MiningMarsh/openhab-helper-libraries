import math

from org.openhab.core.util import ColorUtil
from org.openhab.core.library.types import PercentType


# Constants for Planck's Law and D65 whitepoint
h = 6.62607015e-34  # Planck's constant (Js)
c = 299792458  # Speed of light in vacuum (m/s)
k = 1.380649e-23  # Boltzmann constant (J/K)
D65_X = 95.047/100
D65_Y = 100.000/100
D65_Z = 108.883/100

M = [[0.8951, 0.2664, -0.1614],
        [-0.7502, 1.7135, 0.0367],
        [0.0389, -0.0685, 1.0296]]

M_inv = [[0.9869929, -0.1470543, 0.1599627],
            [0.4323053, 0.5183603, 0.0492912],
            [-0.0085287, 0.040028, 0.9684867]]


def matrix_multiply(mat, vec):
    return [sum(mat[i][j] * vec[j] for j in range(3)) for i in range(3)]


def bradford_transform(src_whitepoint, dest_whitepoint):

    src_cone = matrix_multiply(M, src_whitepoint)
    dest_cone = matrix_multiply(M, dest_whitepoint)    

    scaling = [dest_cone[i] / src_cone[i] if src_cone[i] != 0 else 1 for i in range(3)]

    adapted_M = [[scaling[0] * M[0][0], scaling[0] * M[0][1], scaling[0] * M[0][2]],
                 [scaling[1] * M[1][0], scaling[1] * M[1][1], scaling[1] * M[1][2]],
                 [scaling[2] * M[2][0], scaling[2] * M[2][1], scaling[2] * M[2][2]]]

    transform = [[sum(M_inv[i][k] * adapted_M[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return transform


def spectral_radiance(wavelength, temperature):
    wavelength *= 1e-9
    exponent = (h * c) / (wavelength * k * temperature)
    rterm = 1/(math.exp(exponent)-1)
    lterm = (2*h*c**2)/(wavelength**5)
    return lterm*rterm


def g(x, mu, tau1, tau2):
    if x < mu:
        return math.exp(-((tau1**2) * (x - mu) ** 2) / 2)
    else:
        return math.exp(-((tau2**2) * (x - mu) ** 2) / 2)


def x_bar(wavelength):
    return (
        1.056 * g(wavelength, 599.8, 0.0264, 0.0323)
        + 0.362 * g(wavelength, 442.0, 0.0624, 0.0374)
        - 0.065 * g(wavelength, 501.1, 0.0490, 0.0382)
        - 0.00 * g(wavelength, 512, 0.01,0.01)
    ) 


def y_bar(wavelength):
    return ( 0.821 * g(wavelength, 568.8, 0.0213, 0.0247) 
      + 0.286 * g(wavelength, 530.9, 0.0613, 0.0322)
      - 0.05 * g(wavelength, 650, 0.03, 0.03)

       )


def z_bar(wavelength):
    return 1.217 * g(wavelength, 437.0, 0.0845, 0.0278) + 0.681 * g(
        wavelength, 459.0, 0.0385, 0.0725
    )


def xyz_bar(wavelength):
    return x_bar(wavelength), y_bar(wavelength), z_bar(wavelength)

def mean_xyz(
    temperature, start_wavelength=380, end_wavelength=780, steps=100
):
    delta_lambda = (end_wavelength - start_wavelength) / steps
    X_total, Y_total, Z_total = 0, 0, 0
    normalization = 0

    for i in range(steps):
        wavelength = start_wavelength + i * delta_lambda
        radiance = spectral_radiance(wavelength, temperature)
        X, Y, Z = xyz_bar(wavelength)
        X_total += radiance * X * delta_lambda
        Y_total += radiance * Y * delta_lambda
        Z_total += radiance * Z * delta_lambda

        normalization += radiance * delta_lambda

    X_mean = X_total / normalization if normalization != 0 else 0
    Y_mean = Y_total / normalization if normalization != 0 else 0
    Z_mean = Z_total / normalization if normalization != 0 else 0

    return X_mean, Y_mean, Z_mean


def xyz_d65_to_linear_rgb(X, Y, Z):
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9693 * X + 1.8760 * Y + 0.0416 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0572 * Z
    return r, g, b


def linear_rgb_to_sRGB(r, g, b, temperature):
    def gamma_correct(value):
        return (
            12.92 * value
            if value <= 0.0031308
            else 1.055 * math.pow(value, 1.0 / 2.4) - 0.055
        )

    r = gamma_correct(max(0, min(1, r)))
    g = gamma_correct(max(0, min(1, g)))
    b = gamma_correct(max(0, min(1, b)))
            
    return r, g, b


ADAPTION_MATRICIES = {}


def kelvin_to_xyz_d65(temperature, reference_white_temp=6500):
    if reference_white_temp not in ADAPTION_MATRICIES:
        X_ref, Y_ref, Z_ref = mean_xyz(reference_white_temp, steps=5000)
        print(X_ref,Y_ref)
        wp_transform = bradford_transform([X_ref,Y_ref,Z_ref], [D65_X,D65_Y,D65_Z])
        ADAPTION_MATRICIES[reference_white_temp] = wp_transform
    else:
        wp_transform = ADAPTION_MATRICIES[reference_white_temp]
        
    return matrix_multiply(wp_transform, mean_xyz(temperature,steps=100))


def kelvin_to_sRGB(temperature, reference_white_temp=6500):
    X,Y,Z = kelvin_to_xyz_d65(temperature, reference_white_temp=reference_white_temp)
    if temperature < reference_white_temp:
        beta_left =  0.1
        beta_right =  0.5
        y_left = beta_left*g(temperature, 2700, 1/750.0,1/2000)
        y_right = beta_right*g(temperature, 4500, 1/1200,1/3400)
       
        alpha =  (y_left + y_right)
        Y =  (1-alpha)*Y + alpha*(X + Z)/2
    re,gr,bl = linear_rgb_to_sRGB(*xyz_d65_to_linear_rgb(X,Y,Z),temperature=temperature)
    return re,gr,bl
    

def kelvin_to_hsb(temperature, reference_white_temp=6500):
    return ColorUtil.rgbToHsb(
        (int(i * 255.0) for i in 
         kelvin_to_sRGB(
             temperature, 
             reference_white_temp=reference_white_temp
        ))
    )
