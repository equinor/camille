#include <cmath>
#include <functional>
#include <tuple>
#include <utility>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

static const auto dense = py::array::c_style | py::array::forcecast;

namespace {

struct vec2 {
    double x;
    double y;
};

struct vec3 {
    double x;
    double y;
    double z;
};

struct euler_angles {
    double pitch;
    double roll;
    double yaw;
};

namespace lidar {

struct sample {
    std::uint64_t time;
    int los_id;
    double rws;
    vec3 translation;
    euler_angles rotation;
    vec3 velocity;
    euler_angles angular_velocity;
    int status;
};

struct planar_desc {
    int status;
    double spd;
    double dir;
    double x;
    double y;
    double hgt;
};

struct windfield_desc {
    std::uint64_t time;
    double shear;
    double veer;
    planar_desc upper;
    planar_desc lower;

    std::uint64_t get_time() const noexcept { return time; }
    double get_shear()       const noexcept { return shear; }
    double get_veer()        const noexcept { return veer; }
    double get_status_upr()  const noexcept { return upper.status; }
    double get_status_lwr()  const noexcept { return lower.status; }
    double get_spd_upr()     const noexcept { return upper.spd; }
    double get_spd_lwr()     const noexcept { return lower.spd; }
    double get_dir_upr()     const noexcept { return upper.dir; }
    double get_dir_lwr()     const noexcept { return lower.dir; }
    double get_x_upr()       const noexcept { return upper.x; }
    double get_x_lwr()       const noexcept { return lower.x; }
    double get_y_upr()       const noexcept { return upper.y; }
    double get_y_lwr()       const noexcept { return lower.y; }
    double get_hgt_upr()     const noexcept { return upper.hgt; }
    double get_hgt_lwr()     const noexcept { return lower.hgt; }
};

static const auto sample_pos_docstring = R"(
Parameters
----------
lidar_hgt : float
    Height of the LiDAR
dist : float
    Measurement distance
heave : float
    Vertical offset due to structure motion
pitch : float
roll : float
azm : float
    Line-of-sight azimuth
zn : float
    Line-of-sight zenith

Returns
-------
tuple
    Position of the beam at distance `dist`
)";

vec3 sample_pos(double lidar_hgt,
                double dist,
                double heave,
                double surge,
                double pitch,
                double roll,
                double azm,
                double zn) noexcept {
    using std::sin;
    using std::cos;
    dist = dist / cos(zn);
    return {
        cos(pitch) * dist * cos(zn) +
        sin(pitch) * sin(zn) * dist * (sin(roll) * cos(azm) -
        cos(roll) * sin(azm)) - sin(pitch) * cos(roll) * lidar_hgt + surge,

        sin(zn) * dist * (cos(roll) * cos(azm) + sin(roll) * sin(azm)) +
        sin(roll) * lidar_hgt,

        sin(pitch) * dist * cos(zn) +
        cos(pitch) * sin(zn) * dist * (cos(roll) * sin(azm) -
        sin(roll) * cos(azm)) + cos(pitch) * cos(roll) * lidar_hgt + heave
    };
}

std::tuple<double, double, double> py_sample_pos(double lidar_hgt,
                                                 double dist,
                                                 double heave,
                                                 double surge,
                                                 double pitch,
                                                 double roll,
                                                 double azm,
                                                 double zn) noexcept {
    const auto [x, y, z] = sample_pos(lidar_hgt, dist, heave, surge, pitch,
                                      roll, azm, zn);
    return {x, y, z};
}

static const auto inertial_reference_frame_docstring = R"(
Parameters
----------
velocity : vec3
angular_velocity : euler_angles
position : vec3

Returns
-------
vec3
    Movement of the beam's inertial reference frame
)";

vec3 inertial_reference_frame(vec3 velocity,
                              euler_angles angular_velocity,
                              vec3 position) {
    const auto [deltax, deltay, deltaz] = velocity;
    const auto [w_pitch, w_roll, w_yaw] = angular_velocity;
    const auto [x, y, z] = position;
    return {
        deltax + (w_yaw * y - w_pitch * z),
        deltay + (w_roll * z - w_yaw * x),
        deltaz + (w_pitch * x - w_roll * y),
    };
}

static const auto shear_docstring = R"(
Calculate shear

Parameters
----------
ws_upr : float
    Wind speed of the upper plane
ws_lwr : float
    Wind speed of the lower plane
hgt_upr : float
    Height of the upper plane
hgt_lwr : float
    Height of the lower plane

Returns
-------
float
    Shear

References
----------

.. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law
)";

double shear(double ws_upr,
             double ws_lwr,
             double hgt_upr,
             double hgt_lwr) noexcept {
    using std::log;
    return log(ws_upr / ws_lwr) / log(hgt_upr / hgt_lwr);
}

static const auto veer_docstring = R"(
Calculate vertical wind veer from horizontal directions

Parameters
----------
dir_upr : float
    Wind direction in the upper plane
dir_lwr : float
    Wind direction in the lower plane
hgt_upr : float
    Height of the upper plane
hgt_lwr : float
    Height of the lower plane

Returns
-------
float
    Veer
)";

double veer(double dir_upr,
            double dir_lwr,
            double hgt_upr,
            double hgt_lwr) noexcept {
    using std::atan2;
    using std::sin;
    using std::cos;
    double a = dir_upr - dir_lwr;

    // Normalize angular difference
    double n = atan2(sin(a), cos(a));

    return n / (hgt_upr - hgt_lwr);
}

static const auto planar_windspeed_docstring = R"(
Calculates the wind speed for a horizontal plane given two beams, a and b. a
being the leftmost beam  and b the  rightmost as seen from behind the LiDAR.
The  vector and  orientation  of  the  beams are  given  by the pitch, roll,
zeniths  and azimuths. Measured wind speeds are  given as  radial wind speed
(RWS), that is the actual wind vector as projected onto the beam vector. The
calculation is done by solving the following equations for V, where V is the
wind vector. Ia and Ib are the beams' respective inertial reference frames.

RWSa = R . La . (V - Ia)
RWSb = R . Lb . (V - Ib)

R is  the rotational  matrix Ry(pitch)  .  Rx(roll),  and  L are the LOS, or
Line-Of-Sights, for beam a and b. The beam vector (RL) is given by:

                    Ry(p)                 Rx(r)                 L
             | cos p  0  -sin p | | 1    0       0   | |      cos zn      |
RL = R . L = |   0    1    0    | | 0  cos r   sin r | | sin zn * cos azm |
             | sin p  0  cos p  | | 0  -sin r  cos r | | sin zn * sin azm |

Because the wind speed is projected onto the beam, RL, we have:

           | Vx - Ix |
RWS = RL . | Vy - Iy |
           | Vz - Iz |

If we assume Vz to be 0, we get:

RWSa = RLa_x * (Vx - Ix_a) + RLa_y * (Vy - Iy_a) - RLa_z * Iz_a
     = a0 * (Vx - Ix_a) + a1 * (Vy - Iy_a) - a2 * Iz_a
RWSb = RLb_x * (Vx - Ix_b) + RLb_y * (Vy - Iy_b) - RLb_z * Iz_b
     = b0 * (Vx - Ix_b) + b1 * (Vy - Iy_b) - b2 * Iz_b

Note that we rename RLa_x, RLa_y, RLa_z, RLb_x, RLa_y and RLb_z
to a0, a1, a2, b0, b1, and b2.

Solving for Vx and Vy gives us:

Vx = (a0 * b1 * Ix_a - a1 * b0 * Ix_b + a1 * b1 * (Iy_a - Iy_b) -
      a1 * b2 * Iz_b + a2 * b1 * Iz_a - a1 * RWS_b + b1 * RWS_a) /
     (a0 * b1 - a1 * b0)
Vy = (RWS_a - a0 * (Vx - Ix_a) + a2 * Iz_a) / a1 + Iy_a

The coordinate system is left-handed, X-forward, Y-right and Z-up.

Parameters
----------
rws_a : float
    Measured radial wind speed a
rws_b : float
    Measured radial wind speed b
rotation : euler_angles
    Yaw is assumed to be 0
azm_a : float
    Line-of-sight a azimuth
azm_b : float
    Line-of-sight b azimuth
zn_a : float
    Line-of-sight a zenith
zn_b : float
    Line-of-sight b zenith
inertial_reference_frame_a : vec3
    Inertial reference frame of beam a
inertial_reference_frame_b : vec3
    Inertial reference frame of beam b

Returns
-------
vec2
    Planar wind speed reconstructed from rws_a and rws_b
)";

vec2 planar_windspeed(double rws_a,
                      double rws_b,
                      euler_angles rotation,
                      double azm_a,
                      double azm_b,
                      double zn_a,
                      double zn_b,
                      vec3 inertial_reference_frame_a,
                      vec3 inertial_reference_frame_b) noexcept {
    using std::sin;
    using std::cos;
    const auto [pitch, roll, yaw] = rotation;
    const auto [Ix_a, Iy_a, Iz_a] = inertial_reference_frame_a;
    const auto [Ix_b, Iy_b, Iz_b] = inertial_reference_frame_b;

    double a0 = cos(pitch) * cos(zn_a) +
                cos(azm_a) * sin(pitch) * sin(roll) * sin(zn_a) -
                cos(roll)  * sin(pitch) * sin(zn_a) * sin(azm_a);

    double a1 = cos(roll) * cos(azm_a) * sin(zn_a) +
                sin(roll) * sin(zn_a)  * sin(azm_a);

    double a2 = cos(zn_a) * sin(pitch) -
                cos(pitch) * cos(azm_a) * sin(roll) * sin(zn_a) +
                cos(pitch) * cos(roll) * sin(zn_a) * sin(azm_a);

    double b0 = cos(pitch) * cos(zn_b) +
                cos(azm_b) * sin(pitch) * sin(roll) * sin(zn_b) -
                cos(roll)  * sin(pitch) * sin(zn_b) * sin(azm_b);

    double b1 = cos(roll) * cos(azm_b) * sin(zn_b) +
                sin(roll) * sin(zn_b)  * sin(azm_b);

    double b2 = cos(zn_b) * sin(pitch) -
                cos(pitch) * cos(azm_b) * sin(roll) * sin(zn_b) +
                cos(pitch) * cos(roll) * sin(zn_b) * sin(azm_b);

    double x = (a0 * b1 * Ix_a - a1 * b0 * Ix_b + a1 * b1 * (Iy_a - Iy_b) -
                a1 * b2 * Iz_b + a2 * b1 * Iz_a - a1 * rws_b + b1 * rws_a) /
               (a0 * b1 - a1 * b0);

    double y = (rws_a - a0 * (x - Ix_a) + a2 * Iz_a) / a1 + Iy_a;

    return {x, y};
}

static const auto calc_plane_desc_docstring = R"(
Calculates the windfield of a horizontal plane given two beams, a and b. a
being the leftmost beam and b the rightmost as seen from behind the LiDAR.
The description of the windfield comprises the total wind speed, its magnitude
in x- and y-direction, the direction of the wind vector and the height of
measurement. 

The translational dislocations heave and surge, the angular dislocations pitch
and roll as well as all translational and angular velocities are averaged
between the two beams.

The measurement position and inertial reference frame are calculated for each
beam and the respective coordinates are extracted. They determine the planar
windspeed whose contributions in x- and y-direction define the windfield's
attributes.

The coordinate system is left-handed, X-forward, Y-right and Z-up.

Parameters
----------
beam_a : struct
    Description of beam a
beam_b : struct
    Description of beam b
dist : float
    Measurement distance
lidar_hgt : float
    (fixed)
azm_a : float
    Line-of-sight a azimuth
azm_b : float
    Line-of-sight b azimuth
zn_a : float
    Line-of-sight a zenith
zn_b : float
    Line-of-sight b zenith

Returns
-------
struct
    Windfield in a horizontal plane between the two beams
)";

planar_desc calc_plane_desc(const sample& beam_a,
                            const sample& beam_b,
                            const double dist,
                            const double lidar_hgt,
                            const double azm_a,
                            const double azm_b,
                            const double zn_a,
                            const double zn_b) noexcept {
    using std::sqrt;
    using std::atan2;

    planar_desc desc;

    desc.status = beam_a.status != 0 && beam_b.status != 0 ? 1 : 0;
    if (desc.status == 0) {
        desc.spd = std::nan("");
        desc.dir = std::nan("");
        desc.x = std::nan("");
        desc.y = std::nan("");
        desc.spd = std::nan("");

        return desc;
    }

    const euler_angles rotation = {
        (beam_a.rotation.pitch + beam_b.rotation.pitch) / 2.0,
        (beam_a.rotation.roll + beam_b.rotation.roll) / 2.0,
        0.0
    };

    const auto pos_a = sample_pos(lidar_hgt,
                                  dist,
                                  beam_a.translation.z,
                                  beam_a.translation.x,
                                  beam_a.rotation.pitch,
                                  beam_a.rotation.roll,
                                  azm_a,
                                  zn_a);
    const auto pos_b = sample_pos(lidar_hgt,
                                  dist,
                                  beam_b.translation.z,
                                  beam_b.translation.x,
                                  beam_b.rotation.pitch,
                                  beam_b.rotation.roll,
                                  azm_b,
                                  zn_b);

    const auto I_a = inertial_reference_frame(beam_a.velocity,
                                              beam_a.angular_velocity,
                                              pos_a);
    const auto I_b = inertial_reference_frame(beam_b.velocity,
                                              beam_b.angular_velocity,
                                              pos_b);

    const auto [wind_x, wind_y] = planar_windspeed(
        beam_a.rws, beam_b.rws, rotation, azm_a, azm_b, zn_a, zn_b, I_a, I_b);

    const auto speed = sqrt(wind_x * wind_x + wind_y * wind_y);
    const auto dir = atan2(wind_y, wind_x);

    desc.spd = speed;
    desc.dir = dir;
    desc.x = wind_x;
    desc.y = wind_y;
    desc.hgt = (pos_a.z + pos_b.z) / 2.0;
    return desc;
}

static const auto calc_windfield_desc_docstring = R"(
Calculates the windfield at the moment in question, given the planar wind
descriptions of the upper and lower set of beams.

The windfield's shear and veer are reconstructed from wind speed, wind direction
in and height of both planes.

The coordinate system is left-handed, X-forward, Y-right and Z-up.

Parameters
----------
time : uint64_t
    Timestamp
beam : array of four structs
    Upper right, upper left, lower right and lower left beam
    Beams are ordered
distance : float
    Measurement distance
lidar_hgt : float
    (fixed)
azimuths : array of four floats
    Line-of-sight azimuth of the respective beam
zeniths : array of four floats
    Line-of-sight zenith of the respective beam

Returns
-------
struct
    Extrapolated windfield with shear and veer
)";

windfield_desc calc_windfield_desc(
        const std::uint64_t time,
        const std::array<sample, 4>& beam,
        const double distance,
        const double lidar_hgt,
        const std::array<double, 4>& azimuths,
        const std::array<double, 4>& zeniths) noexcept {
    planar_desc upper_desc = calc_plane_desc(
        beam[0], beam[1],
        distance, lidar_hgt,
        azimuths[0], azimuths[1],
        zeniths[0], zeniths[1]);
    planar_desc lower_desc = calc_plane_desc(
        beam[2], beam[3],
        distance, lidar_hgt,
        azimuths[2], azimuths[3],
        zeniths[2], zeniths[3]);

    windfield_desc wf_desc;
    wf_desc.time = time;
    wf_desc.shear = std::nan("");
    wf_desc.veer = std::nan("");
    wf_desc.upper = std::move(upper_desc);
    wf_desc.lower = std::move(lower_desc);

    if (wf_desc.upper.status == 1 && wf_desc.lower.status == 1) {
        wf_desc.shear = shear(wf_desc.upper.spd, wf_desc.lower.spd,
                              wf_desc.upper.hgt, wf_desc.lower.hgt);
        wf_desc.veer = veer(wf_desc.upper.dir, wf_desc.lower.dir,
                            wf_desc.upper.hgt, wf_desc.lower.hgt);
    }
    return wf_desc;
}

template<typename T>
T* checked_ptr(py::array_t<T, dense>& in,
               const ssize_t expected_ndim,
               const std::vector<ssize_t>& expected_shape) {
    const auto desc = in.request();

    if (desc.ndim != expected_ndim) {
        std::string msg = "Lengths of all columns must be the same";
        throw std::invalid_argument(msg);
    }

    if (desc.shape != expected_shape) {
        std::string msg = "All columns must be one dimensional";
        throw std::invalid_argument(msg);
    }
    return static_cast< T* >(desc.ptr);
}

bool validate_and_sort_samples(const std::array<sample, 4>& b,
                               std::array<sample, 4>& win) noexcept {
    auto valid_los_id = [](const sample& s){
        return 0 <= s.los_id && s.los_id < 4;
    };
    if (!std::all_of(std::begin(b), std::end(b), valid_los_id)) {
        return false;
    }

    std::array<bool, 4> found = {};
    for (int i = 0; i < 4; i++) {
        found[b[i].los_id] = true;
    }

    if (!found[0] || !found[1] || !found[2] || !found[3]) {
        return false;
    }

    win[b[0].los_id] = b[0];
    win[b[1].los_id] = b[1];
    win[b[2].los_id] = b[2];
    win[b[3].los_id] = b[3];

    return true;
}

template<typename F>
auto mkcol(F fn, const std::vector<windfield_desc>& wf_descs) noexcept
        -> py::array_t< decltype(fn(wf_descs.front())), dense > {
    /*
     * Populates a numpy array all instances of one member of the
     * windfield_descs in wf_descs
     */

    // Figure out the return type of this function, and the array element type
    using return_type = decltype(mkcol(fn, wf_descs));
    using T = typename return_type::value_type;

    auto arr = return_type(wf_descs.size());
    auto desc = arr.request();
    auto ptr = static_cast<T*>(desc.ptr);
    for (int i = 0; i < wf_descs.size(); i++) {
        ptr[i] = fn(wf_descs[i]);
    }
    return arr;
}

py::dict core_windfield_desc(py::array_t<std::uint64_t, dense> time,
                             py::array_t<int, dense> los_id,
                             py::array_t<double, dense> rws,
                             py::array_t<double, dense> heave,
                             py::array_t<double, dense> surge,
                             py::array_t<double, dense> pitch,
                             py::array_t<double, dense> roll,
                             py::array_t<double, dense> surge_velocity,
                             py::array_t<double, dense> sway_velocity,
                             py::array_t<double, dense> heave_velocity,
                             py::array_t<double, dense> pitch_velocity,
                             py::array_t<double, dense> roll_velocity,
                             py::array_t<double, dense> yaw_velocity,
                             py::array_t<int, dense> status,
                             const double distance,
                             const double lidar_hgt,
                             const std::array<double, 4>& azimuths,
                             const std::array<double, 4>& zeniths) {
    auto time_desc = time.request();
    if (time_desc.ndim != 1)
        throw std::invalid_argument("Time column not one dimensional");
    auto len = time_desc.shape[0];

    const auto* timep   = static_cast< std::uint64_t* >(time_desc.ptr);
    const auto* los_idp = checked_ptr(los_id, 1, time_desc.shape);
    const auto* rwsp    = checked_ptr(rws,    1, time_desc.shape);
    const auto* heavep  = checked_ptr(heave,  1, time_desc.shape);
    const auto* surgep  = checked_ptr(surge,  1, time_desc.shape);
    const auto* pitchp  = checked_ptr(pitch,  1, time_desc.shape);
    const auto* rollp   = checked_ptr(roll,   1, time_desc.shape);
    const auto* surge_velocityp = checked_ptr(surge_velocity, 1, time_desc.shape);
    const auto* sway_velocityp = checked_ptr(sway_velocity, 1, time_desc.shape);
    const auto* heave_velocityp = checked_ptr(heave_velocity, 1, time_desc.shape);
    const auto* pitch_velocityp = checked_ptr(pitch_velocity, 1, time_desc.shape);
    const auto* roll_velocityp = checked_ptr(roll_velocity, 1, time_desc.shape);
    const auto* yaw_velocityp = checked_ptr(yaw_velocity, 1, time_desc.shape);
    const auto* statusp = checked_ptr(status, 1, time_desc.shape);

    std::vector<sample> beam(len);
    for (int i = 0; i < len; i ++) {
        beam[i].time             = timep[i];
        beam[i].los_id           = los_idp[i];
        beam[i].rws              = rwsp[i];
        beam[i].translation      = { surgep[i]
                                   , 0.0
                                   , heavep[i]
                                   };
        beam[i].rotation         = { pitchp[i]
                                   , rollp[i]
                                   , 0.0
                                   };
        beam[i].velocity         = { surge_velocityp[i]
                                   , sway_velocityp[i]
                                   , heave_velocityp[i]
                                   };
        beam[i].angular_velocity = { pitch_velocityp[i]
                                   , roll_velocityp[i]
                                   , yaw_velocityp[i]
                                   };
        beam[i].status           = statusp[i];
    }

    std::vector<windfield_desc> wf_descs;
    for (int i = 0; i < len - 3; i++) {
        const std::array<sample, 4> b = {
            beam[i], beam[i + 1], beam[i + 2], beam[i + 3],
        };
        const std::uint64_t time = b[0].time;

        std::array<sample, 4> window;
        if (!validate_and_sort_samples(b, window)) {
            continue;
        }

        windfield_desc wf_desc = calc_windfield_desc(
            time, window, distance, lidar_hgt, azimuths, zeniths);

        if (wf_desc.upper.status == 1 || wf_desc.lower.status == 1) {
            wf_descs.push_back(wf_desc);
        }
    }

    using wfi = windfield_desc;

    auto d = py::dict();
    d["time"]       = mkcol(std::mem_fn(&wfi::get_time),       wf_descs);
    d["shear"]      = mkcol(std::mem_fn(&wfi::get_shear),      wf_descs);
    d["veer"]       = mkcol(std::mem_fn(&wfi::get_veer),       wf_descs);
    d["status_upr"] = mkcol(std::mem_fn(&wfi::get_status_upr), wf_descs);
    d["status_lwr"] = mkcol(std::mem_fn(&wfi::get_status_lwr), wf_descs);
    d["speed_upr"]  = mkcol(std::mem_fn(&wfi::get_spd_upr),    wf_descs);
    d["speed_lwr"]  = mkcol(std::mem_fn(&wfi::get_spd_lwr),    wf_descs);
    d["dir_upr"]    = mkcol(std::mem_fn(&wfi::get_dir_upr),    wf_descs);
    d["dir_lwr"]    = mkcol(std::mem_fn(&wfi::get_dir_lwr),    wf_descs);
    d["x_upr"]      = mkcol(std::mem_fn(&wfi::get_x_upr),      wf_descs);
    d["y_upr"]      = mkcol(std::mem_fn(&wfi::get_y_upr),      wf_descs);
    d["x_lwr"]      = mkcol(std::mem_fn(&wfi::get_x_lwr),      wf_descs);
    d["y_lwr"]      = mkcol(std::mem_fn(&wfi::get_y_lwr),      wf_descs);
    d["height_upr"] = mkcol(std::mem_fn(&wfi::get_hgt_upr),    wf_descs);
    d["height_lwr"] = mkcol(std::mem_fn(&wfi::get_hgt_lwr),    wf_descs);
    return d;
}

} // ^ namespace lidar
} // ^ anonymous namespace

PYBIND11_MODULE(core, m) {
    m.def("sample_pos", lidar::py_sample_pos,
                        lidar::sample_pos_docstring);
    m.def("core_windfield_desc", lidar::core_windfield_desc);
}
