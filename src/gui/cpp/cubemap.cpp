// Decent C++ implementation for the panorama -> cubemap algorithm.
// Adapted from https://stackoverflow.com/questions/29678510/convert-21-equirectangular-panorama-to-cube-map
#include <cmath>
#include <algorithm>

#include "conversion.h"


// atan constants
const double a1 = 0.99997726;
const double a3 = -0.33262347;
const double a5 = 0.19354346;
const double a7 = -0.11643287;
const double a9 = 0.05265332;
const double a11 = -0.01172120;


// Decent atan approximation (performant).
inline double atan_approx(double x) {
    double x_sq = x * x;
    return
        x * (a1 + x_sq * (a3 + x_sq * (a5 + x_sq * (a7 + x_sq * (a9 + x_sq * a11)))));
}


// Decent atan2 approximation (performant, definitely enough).
inline double atan2_approx(double y, double x) {
    if (x == 0) {
        return y == 0 ? 0 : y < 0 ? -M_PI_2 : M_PI_2;
    }
    // Ensure input is in [-1, +1]
    bool swap = std::abs(x) < std::abs(y);
    double atan_input = swap ? x / y : y / x;
    // Approximate atan
    double res = atan_approx(atan_input);
    // If swapped, adjust atan output
    res = swap ? (atan_input >= 0.0 ? M_PI_2: -M_PI_2) - res : res;
    // Adjust quadrants
    return x >= 0.0 ? res : res + (y >= 0.0 ? M_PI : -M_PI);
}


struct Coordinates {
    double x, y, z;

    inline void set(int i, int j, Faces face, double edge) {
        switch (face) {
            case FRONT:
                x = 1; y = (i * 2) / edge - 5; z = 3 - (j * 2) / edge;
                return;
            case BACK:
                x = -1; y = 1 - (i * 2) / edge; z = 3 - (j * 2) / edge;
                return;
            case TOP:
                x = 5 - (j * 2) / edge; y = (i * 2) / edge - 5; z = -1;
                return;
            case BOTTOM:
                x = (j * 2) / edge - 1; y = (i * 2) / edge - 5; z = 1;
                return;
            case RIGHT:
                x = 7 - (i * 2) / edge; y = 1; z = 3 - (j * 2) / edge;
                return;
            case LEFT:
                x = (i * 2) / edge - 3; y = -1; z = 3 - (j * 2) / edge;
        }
    }
};


struct RGB {
    int r, g, b;

    inline void set(char* data, int x, int y, int width) {
        int index = (y * width + x) * 3;
        r = data[index] >= 0 ? data[index] : 256 + data[index];
        g = data[index + 1] >= 0 ? data[index + 1] : 256 + data[index + 1];
        b = data[index + 2] >= 0 ? data[index + 2] : 256 + data[index + 2];
    }
};


// Reusable objects for the cubemap processing.
RGB a, b, c, d;
Coordinates coordinates;


// Integer min/max clipping.
inline int clip(int value, int min, int max) {
    return std::min(std::max(value, min), max);
}


// Calculates pixel colour and sets it (for reuse)
inline void set_pixel_colour(
    char* input, int x, int y, int edge_length,
    int width, int height, Faces face, char* r
) {
    coordinates.set(x, y, face, edge_length);
    double u = 2 * edge_length * (atan2_approx(coordinates.y, coordinates.x) + M_PI) / M_PI;
    double v = 2 * edge_length * (M_PI_2 - atan2_approx(
        coordinates.z,
        std::sqrt(coordinates.x * coordinates.x + coordinates.y * coordinates.y))) / M_PI;
    int ui = floor(u);
    int vi = floor(v);
    double mu = u - ui;
    double nu = v - vi;
    a.set(input, ui % width, clip(vi, 0, height - 1), width);
    b.set(input, (ui + 1) % width, clip(vi, 0, height - 1), width);
    c.set(input, ui % width, clip(vi + 1, 0, height - 1), width);
    d.set(input, (ui + 1) % width, clip(vi + 1, 0, height - 1), width);
    *r = round(a.r*(1-mu)*(1-nu) + b.r*(mu)*(1-nu) + c.r*(1-mu)*nu+d.r*mu*nu);
    *(r + 1) = round(a.g*(1-mu)*(1-nu) + b.g*(mu)*(1-nu) + c.g*(1-mu)*nu+d.g*mu*nu);
    *(r + 2) = round(a.b*(1-mu)*(1-nu) + b.b*(mu)*(1-nu) + c.b*(1-mu)*nu+d.b*mu*nu);
}


// Computes an entire cubemap (entirety of all 6 faces).
void set_cubemap(
    char* input, int input_width, int input_height, char* output, volatile bool* cancel
) {
    int edge_length = input_width / 4;
    Faces face, face2;
    int start, stop;
    unsigned index;
    for (int x = 0; x < input_width; ++x) {
        if (*cancel) {
            // Cancelled from Python side.
            return;
        }
        start = edge_length;
        stop = edge_length * 2;
        switch (x / edge_length) {
            case 0: face = BACK; break;
            case 1: face = LEFT; break;
            case 2:
                start = 0;
                stop = edge_length * 3;
                face = FRONT;
                break;
            case 3: face = RIGHT;
        }
        Faces faces[3] {face, BOTTOM, TOP};
        for (int y = start; y < stop; ++y) {
            face2 = faces[(y < edge_length) + 2 * (y >= edge_length * 2)];
            switch (face2) {
                case FRONT:
                    index = ((y - edge_length) * edge_length + x - edge_length * 2) * 3;
                    break;
                case BACK:
                    index = (edge_length * edge_length + (y - edge_length) * edge_length + x) * 3;
                    break;
                case TOP:
                    index = (2 * edge_length * edge_length + (y - edge_length * 2) * edge_length + x - edge_length * 2) * 3;
                    break;
                case BOTTOM:
                    index = (3 * edge_length * edge_length + y * edge_length + x - edge_length * 2) * 3;
                    break;
                case RIGHT:
                    index = (4 * edge_length * edge_length + (y - edge_length) * edge_length + x - edge_length * 3) * 3;
                    break;
                case LEFT:
                    index = (5 * edge_length * edge_length + (y - edge_length) * edge_length + x - edge_length) * 3;
            }
            set_pixel_colour(
                input, x, y, edge_length,
                input_width, input_height, face2, output + index);
        }
    }
}
