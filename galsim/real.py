# Copyright (c) 2012-2014 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#
"""@file real.py
Functions for dealing with RealGalaxy objects and the catalogs that store their data.

The RealGalaxy uses images of galaxies from real astrophysical data (e.g. the Hubble Space
Telescope), along with a PSF model of the optical properties of the telescope that took these
images, to simulate new galaxy images with a different (must be larger) telescope PSF.  A 
description of the simulation method can be found in Section 5 of Mandelbaum et al. (2012; MNRAS, 
540, 1518), although note that the details of the implementation in Section 7 of that work are not 
relevant to the more recent software used here.

This module defines the RealGalaxyCatalog class, used to store all required information about a
real galaxy simulation training sample and accompanying PSF model.  For information about 
downloading GalSim-readable RealGalaxyCatalog data in FITS format, see the RealGalaxy Data Download
page on the GalSim Wiki: 
https://github.com/GalSim-developers/GalSim/wiki/RealGalaxy%20Data%20Download%20Page

The function simReal() takes this information and uses it to simulate a (no-noise-added) image from
some lower-resolution telescope.
"""


import galsim
import utilities
from galsim import GSObject
from galsim import pyfits

class RealGalaxy(GSObject):
    """A class describing real galaxies from some training dataset.  Its underlying implementation
    uses a Convolution instance of an InterpolatedImage (for the observed galaxy) with a
    Deconvolution of another InterpolatedImage (for the PSF).

    This class uses a catalog describing galaxies in some training data (for more details, see the
    RealGalaxyCatalog documentation) to read in data about realistic galaxies that can be used for
    simulations based on those galaxies.  Also included in the class is additional information that
    might be needed to make or interpret the simulations, e.g., the noise properties of the training
    data.

    Because RealGalaxy involved a Deconvolution, `method = 'phot'` is unavailable for the
    drawImage() function.

    Initialization
    --------------
    
        >>> real_galaxy = galsim.RealGalaxy(real_galaxy_catalog, index=None, id=None, random=False, 
        ...                                 rng=None, x_interpolant=None, k_interpolant=None,
        ...                                 flux=None, pad_factor=4, noise_pad_size=0,
        ...                                 gsparams=None)

    This initializes `real_galaxy` with three InterpolatedImage objects (one for the deconvolved
    galaxy, and saved versions of the original HST image and PSF). Note that there are multiple
    keywords for choosing a galaxy; exactly one must be set.  In future we may add more such
    options, e.g., to choose at random but accounting for the non-constant weight factors
    (probabilities for objects to make it into the training sample).  

    Note that tests suggest that for optimal balance between accuracy and speed, `k_interpolant` and
    `pad_factor` should be kept at their default values.  The user should be aware that significant
    inaccuracy can result from using other combinations of these parameters; more details can be
    found in http://arxiv.org/abs/1401.2636, especially table 1, and in comment
    https://github.com/GalSim-developers/GalSim/issues/389#issuecomment-26166621 and the following
    comments.

    @param real_galaxy_catalog  A RealGalaxyCatalog object with basic information about where to
                            find the data, etc.
    @param index            Index of the desired galaxy in the catalog. [One of `index`, `id`, or
                            `random` is required.]
    @param id               Object ID for the desired galaxy in the catalog. [One of `index`, `id`,
                            or `random` is required.]
    @param random           If True, then just select a completely random galaxy from the catalog.
                            [One of `index`, `id`, or `random` is required.]
    @param rng              A random number generator to use for selecting a random galaxy
                            (may be any kind of BaseDeviate or None) and to use in generating
                            any noise field when padding.  This user-input random number
                            generator takes precedence over any stored within a user-input
                            CorrelatedNoise instance (see `noise_pad` parameter below).
                            [default: None]
    @param x_interpolant    Either an Interpolant2d (or Interpolant) instance or a string
                            indicating which real-space interpolant should be used.  Options
                            are 'nearest', 'sinc', 'linear', 'cubic', 'quintic', or 'lanczosN'
                            where N should be the integer order to use. [default: Quintic]
    @param k_interpolant    Either an Interpolant2d (or Interpolant) instance or a string
                            indicating which k-space interpolant should be used.  Options are
                            'nearest', 'sinc', 'linear', 'cubic', 'quintic', or 'lanczosN'
                            where N should be the integer order to use.  We strongly recommend
                            leaving this parameter at its default value; see text above for
                            details.  [default: Quintic]
    @param flux             Total flux, if None then original flux in galaxy is adopted without
                            change. [default: None]
    @param pad_factor       Factor by which to pad the Image when creating the
                            InterpolatedImage.  We strongly recommend leaving this parameter
                            at its default value; see text above for details.  [default: 4]
    @param noise_pad_size   If provided, the image will be padded out to this size (in arcsec)
                            with the noise specified in the real galaxy catalog. This is
                            important if you are planning to whiten the resulting image.  You
                            should make sure that the padded image is larger than the postage
                            stamp onto which you are drawing this object.
                            [default: None]
    @param gsparams         An optional GSParams argument.  See the docstring for GSParams for
                            details. [default: None]

    Methods
    -------

    There are no additional methods for RealGalaxy beyond the usual GSObject methods.
    """

    # Initialization parameters of the object, with type information
    _req_params = {}
    _opt_params = { "x_interpolant" : str ,
                    "k_interpolant" : str ,
                    "flux" : float ,
                    "pad_factor" : float,
                    "noise_pad_size" : float,
                  }
    _single_params = [ { "index" : int , "id" : str } ]
    _takes_rng = True
    _takes_logger = True

    # --- Public Class methods ---
    def __init__(self, real_galaxy_catalog, index=None, id=None, random=False,
                 rng=None, x_interpolant=None, k_interpolant=None, flux=None, pad_factor=4,
                 noise_pad_size=0, gsparams=None, logger=None):

        import numpy as np

        if rng is None:
            rng = galsim.BaseDeviate()
        elif not isinstance(rng, galsim.BaseDeviate):
            raise TypeError("The rng provided to RealGalaxy constructor is not a BaseDeviate")
 
        # Code block below will be for galaxy selection; not all are currently implemented.  Each
        # option must return an index within the real_galaxy_catalog.        
        if index is not None:
            if id is not None or random is True:
                raise AttributeError('Too many methods for selecting a galaxy!')
            use_index = index
        elif id is not None:
            if random is True:
                raise AttributeError('Too many methods for selecting a galaxy!')
            use_index = real_galaxy_catalog.getIndexForID(id)
        elif random is True:
            uniform_deviate = galsim.UniformDeviate(rng)
            use_index = int(real_galaxy_catalog.nobjects * uniform_deviate()) 
        else:
            raise AttributeError('No method specified for selecting a galaxy!')

        if logger:
            logger.debug('RealGalaxy %d: Start RealGalaxy constructor.',use_index)


        # read in the galaxy, PSF images; for now, rely on pyfits to make I/O errors.
        self.gal_image = real_galaxy_catalog.getGal(use_index)
        if logger:
            logger.debug('RealGalaxy %d: Got gal_image',use_index)

        self.psf_image = real_galaxy_catalog.getPSF(use_index)
        if logger:
            logger.debug('RealGalaxy %d: Got psf_image',use_index)

        #self.noise = real_galaxy_catalog.getNoise(use_index, rng, gsparams)
        # This is a duplication of the RealGalaxyCatalog.getNoise() function, since we
        # want it to be possible to have the RealGalaxyCatalog in another process, and the
        # BaseCorrelatedNoise object is not picklable.  So we just build it here instead.
        noise_image, pixel_scale, var = real_galaxy_catalog.getNoiseProperties(use_index)
        if logger:
            logger.debug('RealGalaxy %d: Got noise_image',use_index)

        if noise_image is None:
            self.noise = galsim.UncorrelatedNoise(var, rng=rng, scale=pixel_scale, gsparams=gsparams)
        else:
            ii = galsim.InterpolatedImage(noise_image, scale=pixel_scale, normalization="sb",
                                          calculate_stepk=False, calculate_maxk=False,
                                          x_interpolant='linear', gsparams=gsparams)
            self.noise = galsim.correlatednoise._BaseCorrelatedNoise(rng, ii)
            self.noise = self.noise.withVariance(var)
        if logger:
            logger.debug('RealGalaxy %d: Finished building noise',use_index)

        # Save any other relevant information as instance attributes
        self.catalog_file = real_galaxy_catalog.getFileName()
        self.index = use_index
        self.pixel_scale = float(pixel_scale)

        # Convert noise_pad to the right noise to pass to InterpolatedImage
        if noise_pad_size:
            noise_pad = self.noise
        else:
            noise_pad = 0.

        # Build the InterpolatedImage of the PSF.
        self.original_psf = galsim.InterpolatedImage(
            self.psf_image, x_interpolant=x_interpolant, k_interpolant=k_interpolant, 
            flux=1.0, scale=self.pixel_scale, gsparams=gsparams)
        if logger:
            logger.debug('RealGalaxy %d: Made original_psf',use_index)

        # Build the InterpolatedImage of the galaxy.
        # Use the stepK() value of the PSF as a maximum value for stepK of the galaxy.
        # (Otherwise, low surface brightness galaxies can get a spuriously high stepk, which
        # leads to problems.)
        self.original_image = galsim.InterpolatedImage(
                self.gal_image, x_interpolant=x_interpolant, k_interpolant=k_interpolant,
                scale=self.pixel_scale, pad_factor=pad_factor, noise_pad_size=noise_pad_size,
                calculate_stepk=self.original_psf.stepK(),
                calculate_maxk=self.original_psf.maxK(),
                noise_pad=noise_pad, rng=rng, gsparams=gsparams)
        if logger:
            logger.debug('RealGalaxy %d: Made original_image',use_index)

        # If flux is None, leave flux as given by original image
        if flux != None:
            self.original_image = self.original_image.withFlux(flux)

        # Calculate the PSF "deconvolution" kernel
        psf_inv = galsim.Deconvolve(self.original_psf, gsparams=gsparams)
        # Initialize the SBProfile attribute
        GSObject.__init__(
            self, galsim.Convolve([self.original_image, psf_inv], gsparams=gsparams))
        if logger:
            logger.debug('RealGalaxy %d: Made gsobject',use_index)

        # Save the noise in the image as an accessible attribute
        self.noise = self.noise.convolvedWith(psf_inv, gsparams)
        if logger:
            logger.debug('RealGalaxy %d: Finished building RealGalaxy',use_index)

    def getHalfLightRadius(self):
        raise NotImplementedError("Half light radius calculation not implemented for RealGalaxy "
                                   +"objects.")


class RealGalaxyCatalog(object):
    """Class containing a catalog with information about real galaxy training data.

    The RealGalaxyCatalog class reads in and stores information about a specific training sample of
    realistic galaxies. We assume that all files containing the images (galaxies and PSFs) live in
    one directory; they could be individual files, or multiple HDUs of the same file.  Currently
    there is no functionality that lets this be a FITS data cube, because we assume that the object
    postage stamps will in general need to be different sizes depending on the galaxy size.  

    If only the catalog name (`'real_galaxy_catalog.fits'`) is specified, then the set of galaxy/PSF
    image files (e.g., `'real_galaxy_images_1.fits'`, `'real_galaxy_PSF_images_1.fits'`, etc.) are
    assumed to be in the directory as the catalog file (in the following example, in the current 
    working directory `./`):

        >>> my_rgc = galsim.RealGalaxyCatalog('real_galaxy_catalog.fits')

    If `image_dir` is specified, the set of galaxy/PSF image files is assumed to be in that
    subdirectory of where the catalog is (in the following example, `./images`):

        >>> my_rgc = galsim.RealGalaxyCatalog('real_galaxy_catalog.fits', image_dir='images')

    If the real galaxy catalog is in some far-flung directory, and the galaxy/PSF image files are in 
    its subdirectory, one only needs to specify the long directory name once:

        >>> file_name = '/data3/scratch/user_name/galsim/real_galaxy_data/real_galaxy_catalog.fits'
        >>> image_dir = 'images'
        >>> my_rgc = galsim.RealGalaxyCatalog(file_name, image_dir=image_dir)

    In the above case, the galaxy/PSF image files are in the directory 
    `/data3/scratch/user_name/galsim/real_galaxy_data/images/`.

    The above behavior is changed if the `image_dir` specifies a directory.  In this case, 
    `image_dir` is interpreted as the full path:

        >>> file_name = '/data3/scratch/user_name/galsim/real_galaxy_data/real_galaxy_catalog.fits'
        >>> image_dir = '/data3/scratch/user_name/galsim/real_galaxy_data/images'
        >>> my_rgc = galsim.RealGalaxyCatalog(file_name, image_dir=image_dir)

    When `dir` is specified without `image_dir` being specified, both the catalog and
    the set of galaxy/PSF images will be searched for under the directory `dir`:

        >>> catalog_dir = '/data3/scratch/user_name/galsim/real_galaxy_data'
        >>> file_name = 'real_galaxy_catalog.fits'
        >>> my_rgc = galsim.RealGalaxyCatalog(file_name, dir=catalog_dir)

    If the `image_dir` is specified in addition to `dir`, the catalog name is specified as 
    `dir/file_name`, while the galaxy/PSF image files will be searched for under `dir/image_dir`:

        >>> catalog_dir = '/data3/scratch/user_name/galsim/real_galaxy_data'
        >>> file_name = 'real_galaxy_catalog.fits'
        >>> image_dir = 'images'
        >>> my_rgc = galsim.RealGalaxyCatalog(file_name, image_dir=image_dir, dir=catalog_dir)

    To explore for the future: scaling with number of galaxies, adding more information as needed,
    and other i/o related issues.

    The GalSim repository currently contains an example catalog, in
    `GalSim/examples/data/real_galaxy_catalog_example.fits` (100 galaxies), along with the
    corresponding image data in other files (`real_galaxy_images.fits` and
    `real_galaxy_PSF_images.fits`) in that directory.  For information on how to download a larger
    sample of 26k training galaxies, see the RealGalaxy Data Download Page on the GalSim Wiki:
    https://github.com/GalSim-developers/GalSim/wiki/RealGalaxy%20Data%20Download%20Page

    @param file_name  The file containing the catalog.
    @param image_dir  If a string containing no `/`, it is the relative path from the location of
                      the catalog file to the directory containing the galaxy/PDF images.
                      If a path (a string containing `/`), it is the full path to the directory
                      containing the galaxy/PDF images. [default: None]
    @param dir        The directory of catalog file. [default: None]
    @param preload    Whether to preload the header information.  If `preload=True`, the bulk of 
                      the I/O time is in the constructor.  If `preload=False`, there is
                      approximately the same total I/O time (assuming you eventually use most of
                      the image files referenced in the catalog), but it is spread over the
                      various calls to getGal() and getPSF().  [default: False]
    @param noise_dir  The directory of the noise files if different from the directory of the 
                      image files.  [default: image_dir]
    """
    _req_params = { 'file_name' : str }
    _opt_params = { 'image_dir' : str , 'dir' : str, 'preload' : bool, 'noise_dir' : str }
    _single_params = []
    _takes_rng = False
    _takes_logger = True

    # nobject_only is an intentionally undocumented kwarg that should be used only by
    # the config structure.  It indicates that all we care about is the nobjects parameter.
    # So skip any other calculations that might normally be necessary on construction.
    def __init__(self, file_name, image_dir=None, dir=None, preload=False, nobjects_only=False,
                 noise_dir=None, logger=None):
        import os
        # First build full file_name
        if dir is None:
            self.file_name = file_name
            if image_dir == None:
                self.image_dir = os.path.dirname(file_name)
            elif os.path.dirname(image_dir) == '':
                self.image_dir = os.path.join(os.path.dirname(self.file_name),image_dir)
            else:
                self.image_dir = image_dir
        else:
            self.file_name = os.path.join(dir,file_name)
            if image_dir == None:
                self.image_dir = dir
            else:
                self.image_dir = os.path.join(dir,image_dir)
        if not os.path.isdir(self.image_dir):
            raise RuntimeError(self.image_dir+' directory does not exist!')
        if noise_dir is None:
            self.noise_dir = self.image_dir
        else:
            if not os.path.isdir(noise_dir):
                raise RuntimeError(noise_dir+' directory does not exist!')
            self.noise_dir = noise_dir

        cat = pyfits.getdata(self.file_name)
        self.nobjects = len(cat) # number of objects in the catalog
        if nobjects_only: return  # Exit early if that's all we needed.
        ident = cat.field('ident') # ID for object in the training sample

        # We want to make sure that the ident array contains all strings.
        # Strangely, ident.astype(str) produces a string with each element == '1'.
        # Hence this way of doing the conversion:
        self.ident = [ "%s"%val for val in ident ]

        self.gal_file_name = cat.field('gal_filename') # file containing the galaxy image
        self.psf_file_name = cat.field('PSF_filename') # file containing the PSF image

        # Add the directories:
        self.gal_file_name = [ os.path.join(self.image_dir,f) for f in self.gal_file_name ]
        self.psf_file_name = [ os.path.join(self.image_dir,f) for f in self.psf_file_name ]

        # We don't require the noise_filename column.  If it is not present, we will use
        # Uncorrelated noise based on the variance column.
        try:
            self.noise_file_name = cat.field('noise_filename') # file containing the noise cf
            self.noise_file_name = [ os.path.join(self.noise_dir,f) for f in self.noise_file_name ]
        except:
            self.noise_file_name = None

        self.gal_hdu = cat.field('gal_hdu') # HDU containing the galaxy image
        self.psf_hdu = cat.field('PSF_hdu') # HDU containing the PSF image
        self.pixel_scale = cat.field('pixel_scale') # pixel scale for image (could be different
        # if we have training data from other datasets... let's be general here and make it a 
        # vector in case of mixed training set)
        self.variance = cat.field('noise_variance') # noise variance for image
        self.mag = cat.field('mag')   # apparent magnitude
        self.band = cat.field('band') # bandpass in which apparent mag is measured, e.g., F814W
        self.weight = cat.field('weight') # weight factor to account for size-dependent
                                          # probability

        self.saved_noise_im = {}
        self.loaded_files = {}
        self.logger = logger

        # The pyfits commands aren't thread safe.  So we need to make sure the methods that
        # use pyfits are not run concurrently from multiple threads.
        from multiprocessing import Lock
        self.gal_lock = Lock()  # Use this when accessing gal files
        self.psf_lock = Lock()  # Use this when accessing psf files
        self.loaded_lock = Lock()  # Use this when opening new files from disk
        self.noise_lock = Lock()  # Use this for building the noise image(s) (usually just one)

        # Preload all files if desired
        if preload: self.preload()

        # eventually I think we'll want information about the training dataset, 
        # i.e. (dataset, ID within dataset)
        # also note: will be adding bits of information, like noise properties and galaxy fit params

    def __del__(self):
        # Make sure to clean up pyfits open files if people forget to call close()
        self.close()

    def close(self):
        # Need to close any open files.
        # Make sure to check if loaded_files exists, since the constructor could abort
        # before it gets to the place where loaded_files is built.
        if hasattr(self, 'loaded_files'):
            for f in self.loaded_files.values():
                f.close()
        self.loaded_files = {}

    def getNObjects(self) : return self.nobjects
    def getFileName(self) : return self.file_name

    def getIndexForID(self, id):
        """Internal function to find which index number corresponds to the value ID in the ident 
        field.
        """
        # Just to be completely consistent, convert id to a string in the same way we
        # did above for the ident array:
        id = "%s"%id
        if id in self.ident:
            return self.ident.index(id)
        else:
            raise ValueError('ID %s not found in list of IDs'%id)

    def preload(self):
        """Preload the files into memory.
        
        There are memory implications to this, so we don't do this by default.  However, it can be 
        a big speedup if memory isn't an issue.  Especially if many (or all) of the images are 
        stored in the same file as different HDUs.
        """
        import numpy
        from multiprocessing import Lock
        if self.logger:
            self.logger.debug('RealGalaxyCatalog: start preload')
        for file_name in numpy.concatenate((self.gal_file_name , self.psf_file_name)):
            # numpy sometimes add a space at the end of the string that is not present in 
            # the original file.  Stupid.  But this next line removes it.
            file_name = file_name.strip()
            if file_name not in self.loaded_files:
                if self.logger:
                    self.logger.debug('RealGalaxyCatalog: preloading %s',file_name)
                # I use memmap=False, because I was getting problems with running out of 
                # file handles in the great3 real_gal run, which uses a lot of rgc files.
                # I think there must be a bug in pyfits that leaves file handles open somewhere
                # when memmap = True.  Anyway, I don't know what the performance implications
                # are (since I couldn't finish the run with the default memmap=True), but I
                # don't think there is much impact either way with memory mapping in our case.
                self.loaded_files[file_name] = pyfits.open(file_name,memmap=False)

    def _getFile(self, file_name):
        from multiprocessing import Lock
        if file_name in self.loaded_files:
            if self.logger:
                self.logger.debug('RealGalaxyCatalog: File %s is already open',file_name)
            f = self.loaded_files[file_name]
        else:
            self.loaded_lock.acquire()
            # Check again in case two processes both hit the else at the same time.
            if file_name in self.loaded_files:
                if self.logger:
                    self.logger.debug('RealGalaxyCatalog: File %s is already open',file_name)
                f = self.loaded_files[file_name]
            else:
                if self.logger:
                    self.logger.debug('RealGalaxyCatalog: open file %s',file_name)
                f = pyfits.open(file_name,memmap=False)
                self.loaded_files[file_name] = f
            self.loaded_lock.release()
        return f

    def getGal(self, i):
        """Returns the galaxy at index `i` as an Image object.
        """
        import numpy
        if self.logger:
            self.logger.debug('RealGalaxyCatalog %d: Start getGal',i)
        if i >= len(self.gal_file_name):
            raise IndexError(
                'index %d given to getGal is out of range (0..%d)'%(i,len(self.gal_file_name)-1))
        f = self._getFile(self.gal_file_name[i])
        # For some reason the more elegant `with gal_lock:` syntax isn't working for me.
        # It gives an EOFError.  But doing an explicit acquire and release seems to work fine.
        self.gal_lock.acquire()
        array = f[self.gal_hdu[i]].data
        self.gal_lock.release()
        im = galsim.Image(numpy.ascontiguousarray(array.astype(numpy.float64)))
        return im


    def getPSF(self, i):
        """Returns the PSF at index `i` as an Image object.
        """
        import numpy
        if self.logger:
            self.logger.debug('RealGalaxyCatalog %d: Start getPSF',i)
        if i >= len(self.psf_file_name):
            raise IndexError(
                'index %d given to getPSF is out of range (0..%d)'%(i,len(self.psf_file_name)-1))
        f = self._getFile(self.psf_file_name[i])
        self.psf_lock.acquire()
        array = f[self.psf_hdu[i]].data
        self.psf_lock.release()
        return galsim.Image(numpy.ascontiguousarray(array.astype(numpy.float64)))

    def getNoiseProperties(self, i):
        """Returns the components needed to make the noise correlation function at index `i`.
           Specifically, the noise image (or None), the pixel_scale, and the noise variance,
           as a tuple (im, scale, var).
        """

        if self.logger:
            self.logger.debug('RealGalaxyCatalog %d: Start getNoise',i)
        if self.noise_file_name is None:
            im = None
        else:
            if i >= len(self.noise_file_name):
                raise IndexError(
                    'index %d given to getNoise is out of range (0..%d)'%(
                        i,len(self.noise_file_name)-1))
            if self.noise_file_name[i] in self.saved_noise_im:
                im = self.saved_noise_im[self.noise_file_name[i]]
                if self.logger:
                    self.logger.debug('RealGalaxyCatalog %d: Got saved noise im',i)
            else:
                self.noise_lock.acquire()
                # Again, a second check in case two processes get here at the same time.
                if self.noise_file_name[i] in self.saved_noise_im:
                    im = self.saved_noise_im[self.noise_file_name[i]]
                    if self.logger:
                        self.logger.debug('RealGalaxyCatalog %d: Got saved noise im',i)
                else:
                    import numpy
                    array = pyfits.getdata(self.noise_file_name[i])
                    im = galsim.Image(numpy.ascontiguousarray(array.astype(numpy.float64)))
                    self.saved_noise_im[self.noise_file_name[i]] = im
                    if self.logger:
                        self.logger.debug('RealGalaxyCatalog %d: Built noise im',i)
                self.noise_lock.release()

        return im, self.pixel_scale[i], self.variance[i]

    def getNoise(self, i, rng=None, gsparams=None):
        """Returns the noise correlation function at index `i` as a CorrelatedNoise object.
           Note: the return value from this function is not picklable, so this cannot be used
           across processes.
        """
        im, scale, var = self.getNoiseProperties(i)
        if im is None:
            cf = galsim.UncorrelatedNoise(var, rng=rng, scale=pixel_scale, gsparams=gsparams)
        else:
            ii = galsim.InterpolatedImage(im, scale=scale, normalization="sb",
                                          calculate_stepk=False, calculate_maxk=False,
                                          x_interpolant='linear', gsparams=gsparams)
            cf = galsim.correlatednoise._BaseCorrelatedNoise(rng, ii)
            cf = cf.withVariance(var)
        return cf


def simReal(real_galaxy, target_PSF, target_pixel_scale, g1=0.0, g2=0.0, rotation_angle=None, 
            rand_rotate=True, rng=None, target_flux=1000.0, image=None):
    """Function to simulate images (no added noise) from real galaxy training data.

    This function takes a RealGalaxy from some training set, and manipulates it as needed to 
    simulate a (no-noise-added) image from some lower-resolution telescope.  It thus requires a
    target PSF (which could be an image, or one of our base classes) that represents all PSF 
    components including the pixel response, and a target pixel scale.  

    The default rotation option is to impose a random rotation to make irrelevant any real shears 
    in the galaxy training data (optionally, the RNG can be supplied).  This default can be turned 
    off by setting `rand_rotate = False` or by requesting a specific rotation angle using the
    `rotation_angle` keyword, in which case `rand_rotate` is ignored.

    Optionally, the user can specify a shear (default 0).  Finally, they can specify a flux 
    normalization for the final image, default 1000.

    @param real_galaxy      The RealGalaxy object to use, not modified in generating the
                            simulated image.
    @param target_PSF       The target PSF, either one of our base classes or an Image.
    @param target_pixel_scale  The pixel scale for the final image, in arcsec.
    @param g1               First component of shear to impose (components defined with respect
                            to pixel coordinates), [default: 0]
    @param g2               Second component of shear to impose, [default: 0]
    @param rotation_angle   Angle by which to rotate the galaxy (must be an Angle
                            instance). [default: None]
    @param rand_rotate      Should the galaxy be rotated by some random angle?  [default: True;
                            unless `rotation_angle` is set, then False]
    @param rng              A BaseDeviate instance to use for the random selection or rotation
                            angle. [default: None]
    @param target_flux      The target flux in the output galaxy image, [default: 1000.]
    @param image            As with the GSObject.drawImage() function, if an image is provided,
                            then it will be used and returned.  [default: None, which means an
                            appropriately-sized image will be created.]

    @return a simulated galaxy image.
    """
    # do some checking of arguments
    if not isinstance(real_galaxy, galsim.RealGalaxy):
        raise RuntimeError("Error: simReal requires a RealGalaxy!")
    if isinstance(target_PSF, galsim.Image):
        target_PSF = galsim.InterpolatedImage(target_PSF, scale=target_pixel_scale)
    if not isinstance(target_PSF, galsim.GSObject):
        raise RuntimeError("Error: target PSF is not an Image or GSObject!")
    if rotation_angle != None and not isinstance(rotation_angle, galsim.Angle):
        raise RuntimeError("Error: specified rotation angle is not an Angle instance!")
    if (target_pixel_scale < real_galaxy.pixel_scale):
        import warnings
        message = "Warning: requested pixel scale is higher resolution than original!"
        warnings.warn(message)
    import math # needed for pi, sqrt below
    g = math.sqrt(g1**2 + g2**2)
    if g > 1:
        raise RuntimeError("Error: requested shear is >1!")

    # make sure target PSF is normalized
    target_PSF = target_PSF.withFlux(1.0)

    # rotate
    if rotation_angle != None:
        real_galaxy = real_galaxy.rotate(rotation_angle)
    elif rotation_angle == None and rand_rotate == True:
        if rng == None:
            uniform_deviate = galsim.UniformDeviate()
        elif isinstance(rng,galsim.BaseDeviate):
            uniform_deviate = galsim.UniformDeviate(rng)
        else:
            raise TypeError("The rng provided is not a BaseDeviate")
        rand_angle = galsim.Angle(math.pi*uniform_deviate(), galsim.radians)
        real_galaxy = real_galaxy.rotate(rand_angle)

    # set fluxes
    real_galaxy = real_galaxy.withFlux(target_flux)

    # shear
    if (g1 != 0.0 or g2 != 0.0):
        real_galaxy = real_galaxy.shear(g1=g1, g2=g2)

    # convolve, resample
    out_gal = galsim.Convolve([real_galaxy, target_PSF])
    image = out_gal.drawImage(image=image, scale=target_pixel_scale, method='no_pixel')

    # return simulated image
    return image
