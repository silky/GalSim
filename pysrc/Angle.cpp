/* -*- c++ -*-
 * Copyright (c) 2012-2014 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */
#ifndef __INTEL_COMPILER
#if defined(__GNUC__) && __GNUC__ >= 4 && (__GNUC__ >= 5 || __GNUC_MINOR__ >= 8)
#pragma GCC diagnostic ignored "-Wunused-local-typedefs"
#endif
#endif

#define BOOST_NO_CXX11_SMART_PTR
#include "boost/python.hpp"
#include "Angle.h"

namespace bp = boost::python;

namespace galsim {
namespace {

struct PyAngleUnit {

    static void wrap() {
        bp::class_< AngleUnit > pyAngleUnit("AngleUnit", bp::no_init);
        pyAngleUnit
            .def(bp::init<double>(bp::arg("val")))
            .def(bp::self == bp::self)
            .def("getValue", &AngleUnit::getValue)
            .def(bp::other<double>() * bp::self)
            .enable_pickling()
            ;
    }

};

struct PyAngle {

    static void wrap() {
        bp::class_< Angle > pyAngle("Angle", bp::init<>());
        pyAngle
            .def(bp::init<double, AngleUnit>(bp::args("val","unit")))
            .def(bp::init<const Angle&>(bp::args("rhs")))
            .def("rad", &Angle::rad)
            .def("wrap", &Angle::wrap)
            .def(bp::self / bp::other<AngleUnit>())
            .def(bp::self * bp::other<double>())
            .def(bp::other<double>() * bp::self)
            .def(bp::self / bp::other<double>())
            .def(bp::self + bp::self)
            .def(bp::self - bp::self)
            .def(bp::self == bp::self)
            .def(bp::self != bp::self)
            .def(bp::self <= bp::self)
            .def(bp::self < bp::self)
            .def(bp::self >= bp::self)
            .def(bp::self > bp::self)
            .def(str(bp::self))
            .enable_pickling()
            ;
    }

};

} // anonymous

void pyExportAngle() 
{
    PyAngleUnit::wrap();
    PyAngle::wrap();

    // Also export the global variables:
    bp::scope galsim;
    galsim.attr("radians") = radians;
    galsim.attr("degrees") = degrees;
    galsim.attr("hours") = hours;
    galsim.attr("arcmin") = arcmin;
    galsim.attr("arcsec") = arcsec;
}

} // namespace galsim
