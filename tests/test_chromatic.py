# Copyright 2012-2014 The GalSim developers:
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
#
# GalSim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GalSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GalSim.  If not, see <http://www.gnu.org/licenses/>
#
import os
import numpy as np
from galsim_test_helpers import *
path, filename = os.path.split(__file__)
datapath = os.path.abspath(os.path.join(path, "../examples/data/"))
try:
    import galsim
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

# from pylab import *
# def plotme(image):
#     imshow(image.array)
#     show()

# liberal use of globals here...
zenith_angle = 20 * galsim.degrees
R500 = galsim.dcr.get_refraction(500.0, zenith_angle) # normalize refraction to 500nm

# some profile parameters to test with
bulge_n = 4.0
bulge_hlr = 0.5
bulge_e1 = 0.2
bulge_e2 = 0.2

disk_n = 1.0
disk_hlr = 1.0
disk_e1 = 0.4
disk_e2 = 0.2

PSF_hlr = 0.3
PSF_beta = 3.0
PSF_e1 = 0.01
PSF_e2 = 0.06

shear_g1 = 0.01
shear_g2 = 0.02

# load a filter
bandpass = galsim.Bandpass(os.path.join(datapath, 'LSST_r.dat')).thin()

# load some spectra
bulge_SED = galsim.SED(os.path.join(datapath, 'CWW_E_ext.sed'), wave_type='ang')
bulge_SED = bulge_SED.withFluxDensity(target_flux_density=0.3, wavelength=500.0)

disk_SED = galsim.SED(os.path.join(datapath, 'CWW_Sbc_ext.sed'), wave_type='ang')
disk_SED = disk_SED.withFluxDensity(target_flux_density=0.3, wavelength=500.0)

def test_draw_add_commutativity():
    """Compare two chromatic images, one generated by adding up GSObject profiles before drawing,
    and one generated (via galsim.chromatic) by drawing image summands wavelength-by-wavelength
    while updating the profile and adding as you go.
    """
    import time
    t1 = time.time()

    stamp_size = 32
    pixel_scale = 0.2

    #------------------------------------------------------------------------------
    # Use galsim.base functions to generate chromaticity by creating an effective
    # PSF by adding together weighted monochromatic PSFs.
    # Profiles are added together before drawing.
    #------------------------------------------------------------------------------

    # make galaxy
    GS_gal = galsim.Sersic(n=bulge_n, half_light_radius=bulge_hlr)
    GS_gal = GS_gal.shear(e1=bulge_e1, e2=bulge_e2)
    GS_gal = GS_gal.shear(g1=shear_g1, g2=shear_g2)

    # make effective PSF with Riemann sum midpoint rule
    mPSFs = [] # list of flux-scaled monochromatic PSFs
    N = 50
    h = (bandpass.red_limit * 1.0 - bandpass.blue_limit) / N
    ws = [bandpass.blue_limit + h*(i+0.5) for i in range(N)]
    shift_fn = lambda w:(0, (galsim.dcr.get_refraction(w, zenith_angle) - R500) / galsim.arcsec)
    dilate_fn = lambda w:(w/500.0)**(-0.2)
    for w in ws:
        flux = bulge_SED(w) * bandpass(w) * h
        mPSF = galsim.Moffat(flux=flux, beta=PSF_beta, half_light_radius=PSF_hlr*dilate_fn(w))
        mPSF = mPSF.shear(e1=PSF_e1, e2=PSF_e2)
        mPSF = mPSF.shift(shift_fn(w))
        mPSFs.append(mPSF)
    PSF = galsim.Add(mPSFs)

    # final profile
    pixel = galsim.Pixel(pixel_scale)
    final = galsim.Convolve([GS_gal, PSF, pixel])
    GS_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    t2 = time.time()
    GS_image = final.draw(image=GS_image)
    t3 = time.time()
    print 'GS_object.draw() took {0} seconds.'.format(t3-t2)
    # plotme(GS_image)

    #------------------------------------------------------------------------------
    # Use galsim.chromatic to generate chromaticity.  Internally, this module draws
    # the result at each wavelength and adds the results together.  I.e., drawing
    # and adding happen in the reverse order of the above.
    #------------------------------------------------------------------------------

    # make galaxy
    mono_gal = galsim.Sersic(n=bulge_n, half_light_radius=bulge_hlr)
    chromatic_gal = mono_gal * bulge_SED
    chromatic_gal = chromatic_gal.shear(e1=bulge_e1, e2=bulge_e2)
    chromatic_gal = chromatic_gal.shear(g1=shear_g1, g2=shear_g2)

    # make chromatic PSF
    mono_PSF = galsim.Moffat(beta=PSF_beta, half_light_radius=PSF_hlr)
    mono_PSF = mono_PSF.shear(e1=PSF_e1, e2=PSF_e2)
    chromatic_PSF = galsim.ChromaticObject(mono_PSF)
    chromatic_PSF = chromatic_PSF.dilate(dilate_fn)
    chromatic_PSF = chromatic_PSF.shift(shift_fn)

    # final profile
    chromatic_final = galsim.Convolve([chromatic_gal, chromatic_PSF, pixel])
    chromatic_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    # use chromatic parent class to draw without ChromaticConvolution acceleration...
    t4 = time.time()
    # galsim.ChromaticObject.draw(chromatic_final, bandpass, image=chromatic_image,
    #                             integrator=galsim.integ.midpt_continuous_integrator, N=N)
    integrator = galsim.integ.ContinuousIntegrator(galsim.integ.midpt, N=N, use_endpoints=False)
    galsim.ChromaticObject.draw(chromatic_final, bandpass, image=chromatic_image,
                                integrator=integrator)
    t5 = time.time()
    print 'ChromaticObject.draw() took {0} seconds.'.format(t5-t4)
    # plotme(chromatic_image)

    peak1 = chromatic_image.array.max()

    printval(GS_image, chromatic_image)
    np.testing.assert_array_almost_equal(
        chromatic_image.array/peak1, GS_image.array/peak1, 6,
        err_msg="Directly computed chromatic image disagrees with image created using "
                +"galsim.chromatic")
    t6 = time.time()
    print 'time for %s = %.2f'%(funcname(),t6-t1)

def test_ChromaticConvolution_InterpolatedImage():
    """Check that we can interchange the order of integrating over wavelength and convolving for
    separable ChromaticObjects.  This involves storing the results of integrating first in an
    InterpolatedImage.
    """
    import time
    t1 = time.time()

    pixel_scale = 0.2
    stamp_size = 32

    # stars are fundamentally delta-fns with an SED
    star = galsim.Gaussian(fwhm=1.e-8) * bulge_SED
    pix = galsim.Pixel(pixel_scale)
    mono_PSF = galsim.Gaussian(half_light_radius=PSF_hlr)
    PSF = galsim.ChromaticAtmosphere(mono_PSF, base_wavelength=500.0,
                                     zenith_angle=zenith_angle)

    final = galsim.Convolve([star, PSF, pix])
    image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)

    # draw image using speed tricks in ChromaticConvolution.draw
    # For this particular test, need to set iimult=4 in order to pass.
    II_image = final.draw(bandpass, image=image, iimult=4)
    II_flux = II_image.array.sum()

    image2 = image.copy()
    # draw image without any speed tricks using ChromaticObject.draw
    D_image = galsim.ChromaticObject.draw(final, bandpass, image=image2)
    D_flux = D_image.array.sum()

    #compare
    print 'Flux when integrating first, convolving second: {0}'.format(II_flux)
    print 'Flux when convolving first, integrating second: {0}'.format(D_flux)
    printval(II_image, D_image)
    np.testing.assert_array_almost_equal(
        II_image.array, D_image.array, 5,
        err_msg="ChromaticConvolution draw not equivalent to regular draw")

    # Check flux scaling
    II_image2 = (final * 2.).draw(bandpass, image=image, iimult=4)
    II_flux2 = II_image2.array.sum()
    np.testing.assert_array_almost_equal(
        II_flux2, 2.*II_flux, 5,
        err_msg="ChromaticConvolution * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_chromatic_add():
    """Test the `+` operator on ChromaticObjects"""
    import time
    t1 = time.time()

    stamp_size = 32
    pixel_scale = 0.2

    # create galaxy profiles
    mono_bulge = galsim.Sersic(n=bulge_n, half_light_radius=bulge_hlr)
    bulge = mono_bulge * bulge_SED
    bulge = bulge.shear(e1=bulge_e1, e2=bulge_e2)

    mono_disk = galsim.Sersic(n=disk_n, half_light_radius=disk_hlr)
    disk = mono_disk * disk_SED
    disk = disk.shear(e1=disk_e1, e2=disk_e2)

    # test `+` operator
    bdgal = bulge + disk
    bdgal = bdgal.shear(g1=shear_g1, g2=shear_g2)

    # now shear the indiv profiles
    bulge = bulge.shear(g1=shear_g1, g2=shear_g2)
    disk = disk.shear(g1=shear_g1, g2=shear_g2)

    # create PSF
    mono_PSF = galsim.Moffat(beta=PSF_beta, half_light_radius=PSF_hlr)
    mono_PSF = mono_PSF.shear(e1=PSF_e1, e2=PSF_e2)
    chromatic_PSF = galsim.ChromaticAtmosphere(mono_PSF, base_wavelength=500.0,
                                               zenith_angle=zenith_angle)

    # create final profile
    pixel = galsim.Pixel(pixel_scale)
    final = galsim.Convolve([bdgal, chromatic_PSF, pixel])
    image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    image = final.draw(bandpass, image=image)

    bulge_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    bulge_part = galsim.Convolve([bulge, chromatic_PSF, pixel])
    bulge_image = bulge_part.draw(bandpass, image=bulge_image)
    disk_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    disk_part = galsim.Convolve([disk, chromatic_PSF, pixel])
    disk_image = disk_part.draw(bandpass, image=disk_image)

    piecewise_image = bulge_image + disk_image
    print 'bulge image flux: {0}'.format(bulge_image.array.sum())
    print 'disk image flux: {0}'.format(disk_image.array.sum())
    print 'piecewise image flux: {0}'.format(piecewise_image.array.sum())
    print 'bdimage flux: {0}'.format(image.array.sum())
    printval(image, piecewise_image)
    np.testing.assert_array_almost_equal(
            image.array, piecewise_image.array, 6,
            err_msg="`+` operator doesn't match manual image addition")

    # Check flux scaling
    flux = image.array.sum()
    image = (final * 2.).draw(bandpass, image=image)
    flux2 = image.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="ChromaticConvolution with sum * 2 resulted in wrong flux.")

    # apply flux scaling to ChromaticSum
    final2 = galsim.Convolve(bdgal*2, chromatic_PSF, pixel)
    image = final2.draw(bandpass, image=image)
    flux2 = image.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="ChromaticSum * 2 resulted in wrong flux.")


    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_dcr_moments():
    """Check that zenith-direction surface brightness distribution first and second moments obey
    expected behavior for differential chromatic refraction when comparing objects drawn with
    different SEDs."""

    import time
    t1 = time.time()

    stamp_size = 256
    pixel_scale = 0.025

    # stars are fundamentally delta-fns with an SED
    star1 = galsim.Gaussian(fwhm=1.e-8) * bulge_SED
    star2 = galsim.Gaussian(fwhm=1.e-8) * disk_SED

    shift_fn = lambda w:(0, ((galsim.dcr.get_refraction(w, zenith_angle) - R500)
                             / galsim.arcsec))
    mono_PSF = galsim.Moffat(beta=PSF_beta, half_light_radius=PSF_hlr)
    PSF = galsim.ChromaticObject(mono_PSF)
    PSF = PSF.shift(shift_fn)

    pix = galsim.Pixel(pixel_scale)
    final1 = galsim.Convolve([star1, PSF, pix])
    final2 = galsim.Convolve([star2, PSF, pix])

    image1 = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    image2 = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)

    image1 = final1.draw(bandpass, image=image1)
    image2 = final2.draw(bandpass, image=image2)
    # plotme(image1)

    mom1 = getmoments(image1)
    mom2 = getmoments(image2)
    dR_image = (mom1[1] - mom2[1]) * pixel_scale
    dV_image = (mom1[3] - mom2[3]) * (pixel_scale)**2

    # analytic first moment differences
    R = lambda w:((galsim.dcr.get_refraction(w, zenith_angle) - R500) / galsim.arcsec).astype(float)
    x1 = np.union1d(bandpass.wave_list, bulge_SED.wave_list)
    x1 = x1[(x1 >= bandpass.blue_limit) & (x1 <= bandpass.red_limit)]
    x2 = np.union1d(bandpass.wave_list, disk_SED.wave_list)
    x2 = x2[(x2 >= bandpass.blue_limit) & (x2 <= bandpass.red_limit)]
    numR1 = np.trapz(R(x1) * bandpass(x1) * bulge_SED(x1), x1)
    numR2 = np.trapz(R(x2) * bandpass(x2) * disk_SED(x2), x2)
    den1 = bulge_SED.calculateFlux(bandpass)
    den2 = disk_SED.calculateFlux(bandpass)

    R1 = numR1/den1
    R2 = numR2/den2
    dR_analytic = R1 - R2

    # analytic second moment differences
    V1_kernel = lambda w:(R(w) - R1)**2
    V2_kernel = lambda w:(R(w) - R2)**2
    numV1 = np.trapz(V1_kernel(x1) * bandpass(x1) * bulge_SED(x1), x1)
    numV2 = np.trapz(V2_kernel(x2) * bandpass(x2) * disk_SED(x2), x2)

    V1 = numV1/den1
    V2 = numV2/den2
    dV_analytic = V1 - V2

    print 'image delta R:    {0}'.format(dR_image)
    print 'analytic delta R: {0}'.format(dR_analytic)
    print 'image delta V:    {0}'.format(dV_image)
    print 'analytic delta V: {0}'.format(dV_analytic)
    np.testing.assert_almost_equal(dR_image, dR_analytic, 5,
                                   err_msg="dRbar Shift from DCR doesn't match analytic formula")
    np.testing.assert_almost_equal(dV_image, dV_analytic, 5,
                                   err_msg="dV Shift from DCR doesn't match analytic formula")


    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_chromatic_seeing_moments():
    """Check that surface brightness distribution second moments obey expected behavior
    for chromatic seeing when comparing stars drawn with different SEDs."""

    import time
    t1 = time.time()

    pixel_scale = 0.0075
    stamp_size = 1024

    # stars are fundamentally delta-fns with an SED
    star1 = galsim.Gaussian(fwhm=1e-8) * bulge_SED
    star2 = galsim.Gaussian(fwhm=1e-8) * disk_SED
    pix = galsim.Pixel(pixel_scale)

    indices = [-0.2, 0.6, 1.0]
    for index in indices:

        mono_PSF = galsim.Gaussian(half_light_radius=PSF_hlr)
        PSF = galsim.ChromaticObject(mono_PSF)
        PSF = PSF.dilate(lambda w:(w/500.0)**index)

        final1 = galsim.Convolve([star1, PSF, pix])
        final2 = galsim.Convolve([star2, PSF, pix])

        image1 = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
        image2 = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)

        image1 = final1.draw(bandpass, image=image1)
        image2 = final2.draw(bandpass, image=image2)

        mom1 = getmoments(image1)
        mom2 = getmoments(image2)
        dr2byr2_image = ((mom1[2]+mom1[3]) - (mom2[2]+mom2[3])) / (mom1[2]+mom1[3])

        # analytic moment differences
        x1 = np.union1d(bandpass.wave_list, bulge_SED.wave_list)
        x1 = x1[(x1 <= bandpass.red_limit) & (x1 >= bandpass.blue_limit)]
        x2 = np.union1d(bandpass.wave_list, disk_SED.wave_list)
        x2 = x2[(x2 <= bandpass.red_limit) & (x2 >= bandpass.blue_limit)]
        num1 = np.trapz((x1/500)**(2*index) * bandpass(x1) * bulge_SED(x1), x1)
        num2 = np.trapz((x2/500)**(2*index) * bandpass(x2) * disk_SED(x2), x2)
        den1 = bulge_SED.calculateFlux(bandpass)
        den2 = disk_SED.calculateFlux(bandpass)

        r2_1 = num1/den1
        r2_2 = num2/den2

        dr2byr2_analytic = (r2_1 - r2_2) / r2_1

        np.testing.assert_almost_equal(dr2byr2_image, dr2byr2_analytic, 5,
                                       err_msg="Moment Shift from chromatic seeing doesn't"+
                                               " match analytic formula")

        print 'image delta(r^2) / r^2:    {0}'.format(dr2byr2_image)
        print 'analytic delta(r^2) / r^2: {0}'.format(dr2byr2_analytic)

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_monochromatic_filter():
    """Check that ChromaticObject drawn through a very narrow band filter matches analogous
    GSObject.
    """

    import time
    t1 = time.time()

    pixel_scale = 0.2
    stamp_size = 32

    chromatic_gal = galsim.Gaussian(fwhm=1.0) * bulge_SED
    GS_gal = galsim.Gaussian(fwhm=1.0)

    shift_fn = lambda w:(0, (galsim.dcr.get_refraction(w, zenith_angle) - R500) / galsim.arcsec)
    dilate_fn = lambda wave: (wave/500.0)**(-0.2)
    mono_PSF = galsim.Gaussian(half_light_radius=PSF_hlr)
    mono_PSF = mono_PSF.shear(e1=PSF_e1, e2=PSF_e2)
    chromatic_PSF = galsim.ChromaticObject(mono_PSF)
    chromatic_PSF = chromatic_PSF.dilate(dilate_fn)
    chromatic_PSF = chromatic_PSF.shift(shift_fn)

    pix = galsim.Pixel(pixel_scale)
    chromatic_final = galsim.Convolve([chromatic_gal, chromatic_PSF, pix])

    fws = [350, 475, 625, 750, 875, 975] # approximate ugrizy filter central wavelengths
    for fw in fws:
        chromatic_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
        narrow_filter = galsim.Bandpass(galsim.LookupTable([fw-0.01, fw, fw+0.01],
                                                           [1.0, 1.0, 1.0],
                                                           interpolant='linear'))
        chromatic_image = chromatic_final.draw(narrow_filter, image=chromatic_image)
        # take out normalization
        chromatic_image /= 0.02
        chromatic_image /= bulge_SED(fw)

        # now do non-chromatic version
        GS_PSF = galsim.Gaussian(half_light_radius=PSF_hlr)
        GS_PSF = GS_PSF.shear(e1=PSF_e1, e2=PSF_e2)
        GS_PSF = GS_PSF.dilate(dilate_fn(fw))
        GS_PSF = GS_PSF.shift(shift_fn(fw))
        GS_final = galsim.Convolve([GS_gal, GS_PSF, pix])
        GS_image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
        GS_final.draw(image=GS_image)
        # plotme(GS_image)

        printval(chromatic_image, GS_image)
        np.testing.assert_array_almost_equal(chromatic_image.array, GS_image.array, 5,
                err_msg="ChromaticObject.draw() with monochromatic filter doesn't match"+
                        "GSObject.draw()")

        getmoments(GS_image)
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_chromatic_flux():
    """Test that the total drawn flux is equal to the integral of bandpass * sed over wavelength.
    """
    import time
    t1 = time.time()

    pixel_scale = 0.5
    stamp_size = 64

    # stars are fundamentally delta-fns with an SED
    star = galsim.Gaussian(fwhm=1e-8) * bulge_SED
    pix = galsim.Pixel(pixel_scale)
    mono_PSF = galsim.Gaussian(half_light_radius=PSF_hlr)
    PSF = galsim.ChromaticAtmosphere(mono_PSF, base_wavelength=500,
                                     zenith_angle=zenith_angle)

    final = galsim.Convolve([star, PSF, pix])
    image = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)
    image2 = galsim.ImageD(stamp_size, stamp_size, scale=pixel_scale)

    final.draw(bandpass, image=image)
    ChromaticConvolve_flux = image.array.sum()

    galsim.ChromaticObject.draw(final, bandpass, image=image2)
    ChromaticObject_flux = image2.array.sum()

    # analytic integral...
    analytic_flux = bulge_SED.calculateFlux(bandpass)

    printval(image, image2)
    np.testing.assert_almost_equal(ChromaticObject_flux/analytic_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticObject flux doesn't match " +
                                   "analytic prediction")
    np.testing.assert_almost_equal(ChromaticConvolve_flux/analytic_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "analytic prediction")

    # Try adjusting flux to something else.
    target_flux = 2.63
    bulge_SED2 = bulge_SED.withFlux(target_flux, bandpass)
    star2 = galsim.Gaussian(fwhm=1e-8) * bulge_SED2
    final = galsim.Convolve([star2, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using SED.withFlux()")

    # Use flux_ratio instead.
    flux_ratio = target_flux / analytic_flux
    bulge_SED3 = bulge_SED * flux_ratio
    star3 = galsim.Gaussian(fwhm=1e-8) * bulge_SED3
    final = galsim.Convolve([star3, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using SED * flux_ratio")

    # This should be equivalent.
    bulge_SED3 = flux_ratio * bulge_SED
    star3 = galsim.Gaussian(fwhm=1e-8) * bulge_SED3
    final = galsim.Convolve([star3, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using flux_ratio * SED")

    # Use flux_ratio on the chromatic object instead.
    star4 = star * flux_ratio
    final = galsim.Convolve([star4, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using ChromaticObject * flux_ratio")

    # This should be equivalent.
    star4 = flux_ratio * star
    final = galsim.Convolve([star4, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using flux_ratio * ChromaticObject")

    # As should this.
    star4 = star.withScaledFlux(flux_ratio)
    final = galsim.Convolve([star4, PSF, pix])
    final.draw(bandpass, image=image)
    np.testing.assert_almost_equal(image.array.sum()/target_flux, 1.0, 4,
                                   err_msg="Drawn ChromaticConvolve flux doesn't match " +
                                   "using ChromaticObject.withScaledFlux(flux_ratio)")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_double_ChromaticSum():
    ''' Test logic section of ChromaticConvolve that splits apart ChromaticSums for the case that
    more than one ChromaticSum's are convolved together.
    '''
    import time
    t1 = time.time()

    a = galsim.Gaussian(fwhm=1.0) * bulge_SED
    b = galsim.Gaussian(fwhm=2.0) * bulge_SED
    c = galsim.Gaussian(fwhm=3.0) * bulge_SED
    d = galsim.Gaussian(fwhm=4.0) * bulge_SED

    image = galsim.ImageD(16, 16, scale=0.2)
    obj = galsim.Convolve(a+b, c+d)
    obj.draw(bandpass, image=image)

    image_a = galsim.ImageD(16, 16, scale=0.2)
    image_b = galsim.ImageD(16, 16, scale=0.2)
    obj_a = galsim.Convolve(a, c+d)
    obj_b = galsim.Convolve(b, c+d)
    obj_a.draw(bandpass, image = image_a)
    obj_b.draw(bandpass, image = image_b)
    printval(image, image_a+image_b)

    np.testing.assert_almost_equal(image.array, (image_a+image_b).array, 5,
                                   err_msg="Convolving two ChromaticSums failed")
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticConvolution_of_ChromaticConvolution():
    """Check that the __init__ of ChromaticConvolution properly expands arguments that are already
    ChromaticConvolutions.
    """
    import time
    t1 = time.time()
    a = galsim.Gaussian(fwhm=1.0) * bulge_SED
    b = galsim.Gaussian(fwhm=2.0) * bulge_SED
    c = galsim.Gaussian(fwhm=3.0) * bulge_SED
    d = galsim.Gaussian(fwhm=4.0) * bulge_SED

    e = galsim.Convolve(a, b)
    f = galsim.Convolve(c, d)
    g = galsim.Convolve(e, f)
    if any([not isinstance(h, galsim.Chromatic) for h in g.objlist]):
        raise AssertionError("ChromaticConvolution did not expand ChromaticConvolution argument")
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticAutoConvolution():
    import time
    t1 = time.time()
    a = galsim.Gaussian(fwhm=1.0) * bulge_SED
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    b = galsim.Convolve(a, a)
    b.draw(bandpass, image=im1)
    c = galsim.AutoConvolve(a)
    c.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticAutoConvolution(a) not equal to "
                                         "ChromaticConvolution(a,a)")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (c * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="ChromaticAutoConvolution * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticAutoCorrelation():
    import time
    t1 = time.time()
    a = galsim.Gaussian(fwhm=1.0) * bulge_SED
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    b = galsim.Convolve(a, a.rotate(180.0 * galsim.degrees))
    b.draw(bandpass, image=im1)
    c = galsim.AutoCorrelate(a)
    c.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticAutoCorrelate(a) not equal to "
                                         "ChromaticConvolution(a,a.rotate(180.0*galsim.degrees)")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (c * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="ChromaticAutoCorrelation * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticObject_expand():
    import time
    t1 = time.time()
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    a = galsim.Gaussian(fwhm=1.0).expand(1.1) * bulge_SED
    b = (galsim.Gaussian(fwhm=1.0) * bulge_SED).expand(1.1)

    a.draw(bandpass, image=im1)
    b.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticObject.expand not equal to Chromatic.expand")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (b * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="expanded ChromaticObject * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticObject_rotate():
    import time
    t1 = time.time()
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    a = (galsim.Gaussian(fwhm=1.0)
         .shear(eta=0.1, beta=0 * galsim.degrees)
         .rotate(1.1 * galsim.radians)) * bulge_SED
    b = (((galsim.Gaussian(fwhm=1.0)
           .shear(eta=0.1, beta=0 * galsim.degrees)) * bulge_SED)
           .rotate(1.1 * galsim.radians))

    a.draw(bandpass, image=im1)
    b.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticObject.rotate not equal to Chromatic.rotate")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (b * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="rotated ChromaticObject * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticObject_shear():
    import time
    t1 = time.time()
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    shear = galsim.Shear(g1=0.1, g2=0.1)
    a = galsim.Gaussian(fwhm=1.0).shear(shear) * bulge_SED
    b = (galsim.Gaussian(fwhm=1.0) * bulge_SED).shear(shear)

    a.draw(bandpass, image=im1)
    b.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticObject.shear not equal to Chromatic.shear")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (b * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="rotated ChromaticObject * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticObject_shift():
    import time
    t1 = time.time()
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    shift = (0.1, 0.3)
    a = galsim.Gaussian(fwhm=1.0).shift(shift) * bulge_SED
    b = (galsim.Gaussian(fwhm=1.0) * bulge_SED).shift(shift)

    a.draw(bandpass, image=im1)
    b.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticObject.shift not equal to Chromatic.shift")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (b * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="rotated ChromaticObject * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_ChromaticObject_compound_affine_transformation():
    """ Check that making a (separable) object chromatic before a bunch of transformations is
    equivalent to making it chromatic after a bunch of transformations.
    """
    import time
    t1 = time.time()
    im1 = galsim.ImageD(32, 32, scale=0.2)
    im2 = galsim.ImageD(32, 32, scale=0.2)
    shear = galsim.Shear(eta=1.0, beta=0.3*galsim.radians)
    scale = 1.1
    theta = 0.1 * galsim.radians
    shift = (0.1, 0.3)

    a = galsim.Gaussian(fwhm=1.0)
    a = a.shear(shear).shift(shift).rotate(theta).dilate(scale)
    a = a.shear(shear).shift(shift).rotate(theta).expand(scale)
    a = a.lens(g1=0.1, g2=0.1, mu=1.1).shift(shift).rotate(theta).magnify(scale)
    a = a * bulge_SED

    b = galsim.Gaussian(fwhm=1.0) * bulge_SED
    b = b.shear(shear).shift(shift).rotate(theta).dilate(scale)
    b = b.shear(shear).shift(shift).rotate(theta).expand(scale)
    b = b.lens(g1=0.1, g2=0.1, mu=1.1).shift(shift).rotate(theta).magnify(scale)

    a.draw(bandpass, image=im1)
    b.draw(bandpass, image=im2)
    printval(im1, im2)
    np.testing.assert_array_almost_equal(im1.array, im2.array, 5,
                                         "ChromaticObject affine transformation not equal to "
                                         "GSObject affine transformation")

    # Check flux scaling
    flux = im2.array.sum()
    im2 = (b * 2.).draw(bandpass, image=im2)
    flux2 = im2.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="transformed ChromaticObject * 2 resulted in wrong flux.")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_analytic_integrator():
    """Test that the analytic (i.e., not sampled) versions of SEDs and Bandpasses produce the
    same results as the sampled versions.
    """
    import time
    t1 = time.time()
    pix = galsim.Pixel(0.2)
    psf = galsim.Moffat(fwhm=1.0, beta=2.7)

    # pure analytic
    band1 = galsim.Bandpass('1', blue_limit=500, red_limit=750)
    sed1 = galsim.SED('wave**1.1', flux_type='fphotons').withFluxDensity(1.0, 500)
    gal1 = galsim.Gaussian(fwhm=1.0) * sed1
    final1 = galsim.Convolve(gal1, psf, pix)
    image1 = galsim.ImageD(32, 32, scale=0.2)
    assert len(band1.wave_list) == 0
    assert len(sed1.wave_list) == 0
    final1.draw(band1, image=image1)

    # try making the SED sampled
    band2 = band1
    N = 250 # default N for ContinuousIntegrator
    h = (band2.red_limit*1.0 - band2.blue_limit)/N
    x = [band2.blue_limit + h * i for i in range(N+1)]
    # make a sampled SED
    sed2 = galsim.SED(galsim.LookupTable(x, sed1(x), interpolant='linear'),
                      flux_type='fphotons')
    gal2 = galsim.Gaussian(fwhm=1.0) * sed2
    final2 = galsim.Convolve(gal2, psf, pix)
    image2 = galsim.ImageD(32, 32, scale=0.2)
    assert len(band2.wave_list) == 0
    assert len(sed2.wave_list) != 0
    final2.draw(band1, image=image2)

    # try making the Bandpass sampled
    sed3 = sed1
    band3 = galsim.Bandpass(galsim.LookupTable(x, band1(x), interpolant='linear'))
    gal3 = galsim.Gaussian(fwhm=1.0) * sed3
    final3 = galsim.Convolve(gal3, psf, pix)
    image3 = galsim.ImageD(32, 32, scale=0.2)
    assert len(band3.wave_list) != 0
    assert len(sed3.wave_list) == 0
    final3.draw(band3, image=image3)

    printval(image1, image2)
    np.testing.assert_array_almost_equal(image1.array, image2.array, 5,
                                         "Analytic integrator doesn't match sample integrator")
    printval(image1, image3)
    np.testing.assert_array_almost_equal(image1.array, image3.array, 5,
                                         "Analytic integrator doesn't match sample integrator")
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_gsparam():
    """Check that gsparams actually gets processed by ChromaticObjects.
    """
    import time
    t1 = time.time()
    gal = galsim.ChromaticObject(galsim.Gaussian(fwhm=1))
    pix = galsim.Pixel(0.2)
    gsparams = galsim.GSParams()

    # Setting maximum_fft_size this low causes an exception to be raised for GSObjects, so
    # make sure it does for ChromaticObjects too, thereby assuring that gsparams is really
    # getting properly forwarded through the internals of ChromaticObjects.
    gsparams.maximum_fft_size = 16
    final = galsim.Convolve(gal, pix, gsparams=gsparams)
    np.testing.assert_raises(RuntimeError, final.draw, bandpass)
    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

def test_separable_ChromaticSum():
    """ Test that ChromaticSum separable profile grouping.
    """
    import time
    t1 = time.time()
    psf = galsim.Gaussian(fwhm=1)
    pix = galsim.Pixel(0.2)
    gal1 = galsim.Gaussian(fwhm=1)
    gal2 = galsim.Gaussian(fwhm=1.1)
    gal3 = galsim.Gaussian(fwhm=1.2)

    # check that 2 summands with same SED make a separable sum.
    gal = gal1 * bulge_SED + gal2 * bulge_SED
    img1 = galsim.ImageD(32, 32, scale=0.2)
    if not gal.separable:
        raise AssertionError("failed to identify separable ChromaticSum")

    # check that drawing the profile works as expected
    final = galsim.Convolve(gal, pix, psf)
    final.draw(bandpass, image=img1)

    img2 = galsim.ImageD(32, 32, scale=0.2)
    component1 = galsim.Convolve(gal1*bulge_SED, pix, psf)
    component1.draw(bandpass, image=img2)
    component2 = galsim.Convolve(gal2*bulge_SED, pix, psf)
    component2.draw(bandpass, image=img2, add_to_image=True)

    np.testing.assert_array_almost_equal(img1.array, img2.array, 5,
                                         "separable ChromaticSum not correctly drawn")

    # Check flux scaling
    img3 = galsim.ImageD(32, 32, scale=0.2)
    flux = img1.array.sum()
    img3 = (final * 2).draw(bandpass, image=img3)
    flux2 = img3.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="ChromaticConvolution containing separable ChromaticSum * 2 resulted in wrong flux.")

    final2 = galsim.Convolve(gal * 2, pix, psf)
    img3 = final2.draw(bandpass, image=img3)
    flux2 = img3.array.sum()
    np.testing.assert_array_almost_equal(
        flux2, 2.*flux, 5,
        err_msg="separable ChromaticSum * 2 resulted in wrong flux.")

    # check that 3 summands, 2 with the same SED, 1 with a different SED, make an
    # inseparable sum.
    gal = galsim.Add(gal1 * bulge_SED, gal2 * bulge_SED, gal3 * disk_SED)
    if gal.separable:
        raise AssertionError("failed to identify inseparable ChromaticSum")
    # check that its objlist contains a separable Chromatic and a separable ChromaticSum
    types = dict((o.__class__, o) for o in gal.objlist)
    if galsim.Chromatic not in types or galsim.ChromaticSum not in types:
        raise AssertionError("failed to process list of objects with repeated SED")

    # check that drawing the profile works as expected
    final = galsim.Convolve(gal, pix, psf)
    final.draw(bandpass, image=img1)

    component3 = galsim.Convolve(gal3*disk_SED, pix, psf)
    component3.draw(bandpass, image=img2, add_to_image=True)

    np.testing.assert_array_almost_equal(img1.array, img2.array, 5,
                                         "inseparable ChromaticSum not correctly drawn")

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

if __name__ == "__main__":
    test_draw_add_commutativity()
    test_ChromaticConvolution_InterpolatedImage()
    test_chromatic_add()
    test_dcr_moments()
    test_chromatic_seeing_moments()
    test_monochromatic_filter()
    test_chromatic_flux()
    test_double_ChromaticSum()
    test_ChromaticConvolution_of_ChromaticConvolution()
    test_ChromaticAutoConvolution()
    test_ChromaticAutoCorrelation()
    test_ChromaticObject_expand()
    test_ChromaticObject_rotate()
    test_ChromaticObject_shear()
    test_ChromaticObject_shift()
    test_ChromaticObject_compound_affine_transformation()
    test_analytic_integrator()
    test_gsparam()
    test_separable_ChromaticSum()
