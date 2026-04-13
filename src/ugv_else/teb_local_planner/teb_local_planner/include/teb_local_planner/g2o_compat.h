// Compatibility shim for g2o functions removed in the version shipped with
// ROS 2 Jazzy (ros-jazzy-libg2o 2020.5.29). The g2o::sign and
// g2o::average_angle utilities are no longer in g2o/stuff/misc.h.
#ifndef TEB_LOCAL_PLANNER_G2O_COMPAT_H_
#define TEB_LOCAL_PLANNER_G2O_COMPAT_H_

#include <cmath>

namespace g2o {

template <typename T>
inline int sign(const T& x) {
  return (x > T(0)) - (x < T(0));
}

inline double average_angle(double a, double b) {
  return std::atan2(std::sin(a) + std::sin(b), std::cos(a) + std::cos(b));
}

}  // namespace g2o

#endif  // TEB_LOCAL_PLANNER_G2O_COMPAT_H_
