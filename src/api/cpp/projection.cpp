// C++ implementation for projection rendering, including
// a Matrix class implementation
// with only the required matrix operations implemented.

// Uncomment this line to include displaying to console for debugging only.
// #define DEBUG
#ifdef DEBUG
    #include <iostream>
#endif
#include <algorithm>
#include <cmath>
#include <memory>

#include "conversion.h"


// Very simple matrix class containing only required matrix operations.
class Matrix {
    private:
        std::unique_ptr<double[]> elements;
        unsigned rows, columns;
    public:
        Matrix(unsigned rows, unsigned columns);
        Matrix(unsigned, unsigned, double* initial, unsigned initial_count);
        // Retrieve value at (row, column) [0-indexed].
        inline double& operator()(unsigned row, unsigned column) const;
        // Output for debugging.
        #ifdef DEBUG
            friend std::ostream& operator <<(std::ostream&, const Matrix&);
        #endif
};


Matrix::Matrix(unsigned rows, unsigned columns) {
    this->rows = rows;
    this->columns = columns;
    elements = std::unique_ptr<double[]> {new double[rows * columns] {0}};
}
Matrix::Matrix(
    unsigned rows, unsigned columns, double* initial,
    unsigned initial_count = 0
) : Matrix::Matrix(rows, columns) {
    if (initial_count == 0) {
        // Assume if not set, entire matrix is to be filled.
        initial_count = rows * columns;
    }
    for (unsigned i = 0; i < initial_count; ++i) {
        elements[i] = initial[i];
    }
}


double& Matrix::operator()(unsigned row, unsigned column = 0) const {
    return elements[row * columns + column];
};


#ifdef DEBUG
std::ostream& operator <<(std::ostream& output, const Matrix& matrix) {
    for (int row = 0; row < matrix.rows; ++row) {
        for (int column = 0; column < matrix.columns; ++column) {
            output << matrix(row, column) << ' ';
        }
        output << '\n';
    }
    return output;
};
#endif


// Returns the 3x3 transformation matrix for a given
// pitch and yaw angle for a camera at the origin.
// This matrix transforms from camera to world coordinates.
// Due to nature of problem, 4th dimension (w) not required.
Matrix get_transformation_matrix(double pitch, double yaw) {
    // Degrees to radians.
    pitch *= M_PI / 180;
    yaw *= M_PI / 180;
    double camera_to_world_raw[] {
        -sin(pitch), -sin(yaw) *  cos(pitch), -cos(yaw) * cos(pitch),
        0, cos(yaw), -sin(yaw),
        cos(pitch), -sin(yaw) * sin(pitch), -cos(yaw) * sin(pitch)
    };
    return Matrix(3, 3, camera_to_world_raw);
}


// Double min/max clipping
inline double clip(double value, double min, double max) {
    return std::min(std::max(value, min), max);
}


// Sets a single output pixel in the overall 2D projection.
inline void set_output_pixel(
    int x, int y, char* output, int width,
    const Matrix& direction, int face_length, char* cubemap = nullptr
) {
    int half_face_length = face_length / 2;
    double x1, y1, z1, abs_max, abs_x, abs_y, abs_z;
    x1 = direction(0); y1 = direction(1); z1 = direction(2);
    abs_x = std::abs(x1); abs_y = std::abs(y1); abs_z = std::abs(z1);
    Faces face;
    // Determines first face that is hit going in a given direction.
    if (abs_x > abs_y && abs_x > abs_z) {
        face = x1 > 0 ? RIGHT : LEFT;
        abs_max = abs_x;
    } else if (abs_y > abs_x && abs_y > abs_z) {
        face = y1 > 0 ? TOP : BOTTOM;
        abs_max = abs_y;
    } else {
        face = z1 > 0 ? FRONT : BACK;
        abs_max = abs_z;
    }
    double lambda = half_face_length / abs_max;
    // Transforms direction column vector to the point of intersection
    // of line and face plane.
    x1 *= lambda; y1 *= lambda; z1 *= lambda;
    int x2, y2;

    switch (face) {
        case FRONT:
            x1 = round(clip(x1, -half_face_length, half_face_length - 1));
            y1 = round(clip(y1, -half_face_length, half_face_length - 1));
            x2 = x1 + half_face_length; y2 = y1 + half_face_length;
            break;
        case BACK:
            x1 = round(clip(x1, -half_face_length + 1, half_face_length));
            y1 = round(clip(y1, -half_face_length, half_face_length - 1));
            x2 = half_face_length - x1; y2 = y1 + half_face_length;
            break;
        case TOP:
            x1 = round(clip(x1, -half_face_length, half_face_length - 1));
            z1 = round(clip(z1, -half_face_length + 1, half_face_length));
            x2 = x1 + half_face_length; y2 = half_face_length - z1;
            break;
        case BOTTOM:
            x1 = round(clip(x1, -half_face_length, half_face_length - 1));
            z1 = round(clip(z1, -half_face_length, half_face_length - 1));
            x2 = x1 + half_face_length; y2 = z1 + half_face_length;
            break;
        case RIGHT:
            y1 = round(clip(y1, -half_face_length, half_face_length - 1));
            z1 = round(clip(z1, -half_face_length + 1, half_face_length));
            y2 = y1 + half_face_length; x2 = half_face_length - z1;
            break;
        case LEFT:
            y1 = round(clip(y1, -half_face_length, half_face_length - 1));
            z1 = round(clip(z1, -half_face_length, half_face_length - 1));
            y2 = y1 + half_face_length; x2 = z1 + half_face_length;
    }
    unsigned index = (y * width + (width - x)) * 3;
    // Use pre-built cubemap result..
    unsigned cubemap_index = (
        face * face_length * face_length + y2 * face_length + x2) * 3;
    output[index] = cubemap[cubemap_index];
    output[index + 1] = cubemap[cubemap_index + 1];
    output[index + 2] = cubemap[cubemap_index + 2];
}


// Projects a 2D image given the input image, angles, zoom and output,
// and optionally, a pre-built cubemap to speed up the process.
void project(
    char* output, int output_width, int output_height,
    double pitch, double yaw, double fov, char* cubemap, int face_length
) {
    // Conversions converting pitch angle to be CW,
    // and yaw to go from [-90, 90] instead of [0, 180] (also CW).
    pitch = 360 - pitch;
    yaw = -(yaw - 90);
    Matrix transform_matrix = get_transformation_matrix(pitch, yaw);
    Matrix direction {3, 1};
    double fov_constant =  1 / tan(fov * M_PI / 360);
    double x1, y1, prev_x;
    // Performance optimisation - use same direction matrix object
    // adjusting it as required per pixel.
    for (int y = 0; y < output_height; ++y) {
        y1 = ((double)y * 2 / output_height - 1) / fov_constant;
        direction(0) = y1 * transform_matrix(0, 1) - transform_matrix(0, 2);
        direction(1) = y1 * transform_matrix(1, 1) - transform_matrix(1, 2);
        direction(2) = y1 * transform_matrix(2, 1) - transform_matrix(2, 2);
        prev_x = 0;
        for (int x = 0; x < output_width; ++x) {
            x1 = ((double)x * 2 / output_width - 1) / fov_constant;
            direction(0) += (x1 - prev_x) * transform_matrix(0);
            direction(1) += (x1 - prev_x) * transform_matrix(1);
            direction(2) += (x1 - prev_x) * transform_matrix(2);
            set_output_pixel(
                x, y, output, output_width, direction, face_length, cubemap);
            prev_x = x1;
        }
    }
}
