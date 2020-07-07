"""Processing module that handles loading of data from various file formats"""
# Standard library imports
import os
import math
import time
import logging
from sys import platform
from copy import deepcopy
from typing import Dict
from typing import List
from typing import Optional

# Third-party imports
import numpy as np

# Local imports
from origami.utils.check import check_axes_spacing
from origami.objects.misc import FileItem
from origami.config.config import CONFIG
from origami.objects.groups import MassSpectrumGroup
from origami.readers.io_mgf import MGFReader
from origami.readers.io_mzml import mzMLReader
from origami.utils.utilities import time_loop
from origami.utils.utilities import report_time
from origami.objects.document import DocumentStore
from origami.utils.decorators import check_os
from origami.utils.exceptions import NoIonMobilityDatasetError
from origami.config.environment import ENV
from origami.objects.containers import IonHeatmapObject
from origami.objects.containers import MobilogramObject
from origami.objects.containers import ChromatogramObject
from origami.objects.containers import MassSpectrumObject
from origami.objects.containers import StitchIonHeatmapObject
from origami.objects.containers import ImagingIonHeatmapObject
from origami.objects.containers import MassSpectrumHeatmapObject
from origami.processing.heatmap import equalize_heatmap_spacing
from origami.processing.imaging import ImagingNormalizationProcessor
from origami.readers.io_text_files import TextHeatmapReader
from origami.readers.io_text_files import TextSpectrumReader
from origami.readers.io_text_files import AnnotatedDataReader

# enable on windowsOS only
if platform == "win32":
    from origami.readers.io_waters_raw_api import WatersRawReader
    from origami.readers.io_waters_raw import WatersIMReader

LOGGER = logging.getLogger(__name__)

MGF_N_SCANS = 50000
MZML_N_SCANS = 50000


def check_path(path: str, extension: Optional[str] = None):
    """Check whether path is correct"""
    if not os.path.exists(path):
        raise ValueError(f"Path `{path}` does not exist")
    if extension is not None and not path.endswith(extension):
        raise ValueError(f"Path `{path}` does not have the correct extension")


class LoadHandler:
    """Data load handler"""

    @staticmethod
    @check_os("win32")
    def waters_extract_ms_from_mobilogram(x_min: int, x_max: int, title=None):
        """Extract mass spectrum based on drift time selection

        Parameters
        ----------
        x_min : int
            start drift time in bins
        x_max : int
            end drift time in bins
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        obj_data : MassSpectrumObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("ion_mobility")
        if reader is None:
            path = document.get_file_path("main")
            reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
            document.add_reader("ion_mobility", reader)

        # extract data
        mz_obj = reader.extract_ms(dt_start=x_min, dt_end=x_max, return_data=True)
        obj_name = f"DT_{x_min}-{x_max}"
        mz_obj = document.add_spectrum(obj_name, mz_obj)

        return obj_name, mz_obj, document

    @staticmethod
    @check_os("win32")
    def waters_extract_ms_from_chromatogram(x_min: float, x_max: float, title=None):
        """Extract mass spectrum based on retention time selection

        Parameters
        ----------
        x_min : float
            start retention time in minutes
        x_max : float
            end retention time in minutes
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        obj_data : MassSpectrumObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("ion_mobility")
        if reader is None:
            path = document.get_file_path("main")
            reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
            document.add_reader("ion_mobility", reader)

        mz_obj = reader.extract_ms(rt_start=x_min, rt_end=x_max, return_data=True)
        obj_name = f"RT_{x_min:.2f}-{x_max:.2f}"
        mz_obj = document.add_spectrum(obj_name, mz_obj)

        return obj_name, mz_obj, document

    @staticmethod
    @check_os("win32")
    def waters_extract_ms_from_heatmap(x_min: float, x_max: float, y_min: int, y_max: int, title=None):
        """Extract mass spectrum based on retention time selection

        Parameters
        ----------
        x_min : float
            start retention time in minutes
        x_max : float
            end retention time in minutes
        y_min : int
            start drift time in bins
        y_max : int
            end drift time in bins
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        mz_obj : MassSpectrumObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("ion_mobility")
        if reader is None:
            path = document.get_file_path("main")
            reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
            document.add_reader("ion_mobility", reader)

        mz_obj = reader.extract_ms(rt_start=x_min, rt_end=x_max, dt_start=y_min, dt_end=y_max, return_data=True)
        obj_name = f"RT_{x_min:.2f}-{x_max:.2f}_DT_{y_min}-{y_max}"
        mz_obj = document.add_spectrum(obj_name, mz_obj)

        return obj_name, mz_obj, document

    @staticmethod
    @check_os("win32")
    def waters_extract_rt_from_msdt(x_min: float, x_max: float, y_min: int, y_max: int, title=None):
        """Extract mass spectrum based on retention time selection

        Parameters
        ----------
        x_min : float
            start m/z value
        x_max : float
            end m/z value
        y_min : int
            start drift time in bins
        y_max : int
            end drift time in bins
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        mz_obj : ChromatogramObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("ion_mobility")
        if reader is None:
            path = document.get_file_path("main")
            reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
            document.add_reader("ion_mobility", reader)

        mz_obj = reader.extract_rt(mz_start=x_min, mz_end=x_max, dt_start=y_min, dt_end=y_max, return_data=True)
        obj_name = f"MZ_{x_min:.2f}-{x_max:.2f}_DT_{y_min}-{y_max}"
        mz_obj = document.add_chromatogram(obj_name, mz_obj)

        return obj_name, mz_obj, document

    @staticmethod
    @check_os("win32")
    def waters_extract_heatmap_from_mass_spectrum_one(x_min: float, x_max: float, title=None):
        """Extract heatmap based on mass spectrum range

        Parameters
        ----------
        x_min : float
            start m/z value
        x_max : float
            end m/z value
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        heatmap_obj : IonHeatmapObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("ion_mobility")
        if reader is None:
            path = document.get_file_path("main")
            reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
            document.add_reader("ion_mobility", reader)

        # get heatmap
        heatmap_obj = reader.extract_heatmap(mz_start=x_min, mz_end=x_max, return_data=True)
        obj_name = f"MZ_{x_min:.2f}-{x_max:.2f}"
        heatmap_obj = document.add_heatmap(obj_name, heatmap_obj)

        return obj_name, heatmap_obj, document

    @staticmethod
    @check_os("win32")
    def waters_extract_heatmap_from_mass_spectrum_many(x_min: float, x_max: float, filelist: Dict, title=None):
        """Extract heatmap based on mass spectrum range

        Parameters
        ----------
        x_min : float
            start m/z value
        x_max : float
            end m/z value
        filelist : Dict
            dictionary with filename : variable mapping
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        obj_data : IonHeatmapObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        # document = ENV.on_get_document(title)
        n_files = len(filelist)

        dt_x = np.arange(1, 201)
        array = np.zeros((200, n_files))
        rt_x = []
        for idx, (filepath, value) in enumerate(filelist.items()):
            reader = WatersIMReader(filepath, temp_dir=CONFIG.temporary_data)
            dt_obj = reader.extract_dt(mz_start=x_min, mz_end=x_max, return_data=True)
            array[:, idx] = dt_obj.y
            rt_x.append(value)

        rt_x = np.asarray(rt_x)

        if not check_axes_spacing(rt_x):
            rt_x, dt_x, array = equalize_heatmap_spacing(rt_x, dt_x, array)

        # sum retention time and mobilogram
        rt_y = array.sum(axis=0)
        dt_y = array.sum(axis=1)

        obj_name = f"{x_min:.2f}-{x_max:.2f}"
        obj_data = IonHeatmapObject(array, x=dt_x, y=rt_x, xy=dt_y, yy=rt_y)

        return obj_name, obj_data, None

    @staticmethod
    @check_os("win32")
    def waters_im_extract_ms(path, **kwargs) -> MassSpectrumObject:
        """Extract chromatographic data"""
        check_path(path)
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        mz_obj: MassSpectrumObject = reader.extract_ms(**kwargs)

        return mz_obj

    @staticmethod
    @check_os("win32")
    def waters_im_extract_rt(path, **kwargs) -> ChromatogramObject:
        """Extract chromatographic data"""
        check_path(path)
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        rt_obj: ChromatogramObject = reader.extract_rt(**kwargs)

        return rt_obj

    @staticmethod
    @check_os("win32")
    def waters_im_extract_dt(path, **kwargs) -> MobilogramObject:
        """Extract mobility data"""
        check_path(path)
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        dt_obj: MobilogramObject = reader.extract_dt(**kwargs)

        return dt_obj

    @staticmethod
    @check_os("win32")
    def waters_im_extract_heatmap(path, **kwargs) -> IonHeatmapObject:
        """Extract mobility data"""
        check_path(path)
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        heatmap_obj: IonHeatmapObject = reader.extract_heatmap(**kwargs)

        return heatmap_obj

    @staticmethod
    @check_os("win32")
    def waters_im_extract_msdt(
        path, mz_min: float, mz_max: float, mz_bin_size: float = 1.0, **kwargs
    ) -> MassSpectrumHeatmapObject:
        """Extract mobility data"""
        check_path(path)

        # calculate number of m/z bins
        n_mz_bins = math.floor((mz_max - mz_min) / mz_bin_size)
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        mzdt_obj: MassSpectrumHeatmapObject = reader.extract_msdt(
            mz_start=mz_min, mz_end=mz_max, n_points=n_mz_bins, **kwargs
        )

        return mzdt_obj

    @staticmethod
    @check_os("win32")
    def thermo_extract_ms_from_chromatogram(x_min: float, x_max: float, as_scan: bool, title=None):
        """Extract mass spectrum based on retention time selection

        Parameters
        ----------
        x_min : float
            start retention time in minutes
        x_max : float
            end retention time in minutes
        as_scan : bool
            flag to indicate whether range is provided in correct format
        title: str, optional
            document title

        Returns
        -------
        obj_name : str
            name of the data object
        obj_data : MassSpectrumObject
            dictionary containing extracted data
        document : Document
            instance of the document for which data was extracted
        """
        from origami.readers.io_thermo_raw import ThermoRawReader

        document = ENV.on_get_document(title)

        # setup file reader
        reader = document.get_reader("data_reader")
        if reader is None:
            path = document.get_file_path("main")
            reader = ThermoRawReader(path)
            document.add_reader("data_reader", reader)

        mz_obj = reader.get_spectrum(start_scan=x_min, end_scan=x_max, rt_as_scan=as_scan)
        obj_name = f"RT_{x_min:.2f}-{x_max:.2f}"
        mz_obj = document.add_spectrum(obj_name, mz_obj)

        return obj_name, mz_obj, document

    def document_extract_lesa_image_from_ms(self, x_min: float, x_max: float, title: str):
        """Extract image data for LESA document based on extraction range in the mass spectrum window"""
        from origami.processing.utils import find_nearest_index

        document = ENV.on_get_document(title)
        metadata = document.get_config("imaging")
        shape = (metadata["x_dim"], metadata["y_dim"])
        array = np.zeros(np.dot(*shape))
        changed = True
        for spectrum in document.MassSpectra.values():
            # get variable from the document
            variable = spectrum.attrs.get("file_info", dict()).get("variable", -1) - 1
            if variable < 0:
                continue
            mz_obj = document.as_object(spectrum)
            x_idx_min, x_idx_max = find_nearest_index(mz_obj.x, [x_min, x_max])
            if x_idx_min == x_idx_max:
                x_idx_min -= 1
                x_idx_max += 1
                x_min = mz_obj.x[x_idx_min]
                x_max = mz_obj.x[x_idx_max]
                changed = True
            array[variable] = mz_obj.y[x_idx_min:x_idx_max].sum()

        # notify user that window was widened
        if changed:
            LOGGER.warning(f"The m/z range was too narrow so it was widened to {x_min:.2f}-{x_max:.2f}")

        # reshape object
        array = np.reshape(array, shape)
        obj = ImagingIonHeatmapObject(np.flipud(array))
        name = f"MZ_{x_min:.2f}-{x_max:.2f}"

        return name, obj

    def document_extract_lesa_image_from_dt(
        self, x_min: float, x_max: float, y_min: float, y_max: float, title: str, get_quick: bool = False
    ):
        """Extract image data for LESA document based on extraction range in the mass spectrum + drift time window"""
        from origami.processing.utils import find_nearest_index

        document = ENV.on_get_document(title)
        metadata = document.get_config("imaging")
        shape = (metadata["x_dim"], metadata["y_dim"])
        array = np.zeros(np.dot(*shape))
        changed = False
        for heatmap in document.MSDTHeatmaps.values():
            # get variable from the document
            variable = heatmap.attrs.get("file_info", dict()).get("variable", -1) - 1
            if variable < 0:
                continue
            msdt_obj = document.as_object(heatmap)
            x_idx_min, x_idx_max = find_nearest_index(msdt_obj.x, [x_min, x_max])
            y_idx_min, y_idx_max = find_nearest_index(msdt_obj.y, [y_min, y_max])

            # in some cases, the extraction window is too narrow in which case the window should be widened by 1 bin in
            # each direction
            if x_idx_min == x_idx_max:
                x_idx_min -= 1
                x_idx_max += 1
                x_min = msdt_obj.x[x_idx_min]
                x_max = msdt_obj.x[x_idx_max]
                changed = True
            array[variable] = msdt_obj.array[y_idx_min:y_idx_max, x_idx_min:x_idx_max].sum()

        # notify user that window was widened
        if changed:
            LOGGER.warning(f"The m/z range was too narrow so it was widened to {x_min:.2f}-{x_max:.2f}")

        # reshape object
        array = np.reshape(array, shape)
        obj = ImagingIonHeatmapObject(np.flipud(array))
        name = f"MZ_{x_min:.2f}-{x_max:.2f}_DT_{int(y_min)}-{int(y_max)}"

        return name, obj

    def document_extract_dt_from_msdt_multifile(self, x_min: float, x_max: float, title: str):
        """Extract mobilogram from MS/DT dataset based on mass selection"""
        from origami.processing.utils import find_nearest_index

        document = ENV.on_get_document(title)
        x, y = None, None
        changed = False
        for heatmap in document.MSDTHeatmaps.values():
            # get variable from the document
            variable = heatmap.attrs.get("file_info", dict()).get("variable", -1) - 1
            if variable < 0:
                continue
            msdt_obj = document.as_object(heatmap)
            if x is None:
                x = msdt_obj.y
            if y is None:
                y = np.zeros_like(x, dtype=np.float64)
            x_idx_min, x_idx_max = find_nearest_index(msdt_obj.x, [x_min, x_max])

            # in some cases, the extraction window is too narrow in which case the window should be widened by 1 bin in
            # each direction
            if x_idx_min == x_idx_max:
                x_idx_min -= 1
                x_idx_max += 1
                x_min = msdt_obj.x[x_idx_min]
                x_max = msdt_obj.x[x_idx_max]
                changed = True

            y += msdt_obj.array[:, x_idx_min:x_idx_max].sum(axis=1)

        # notify user that window was widened
        if changed:
            LOGGER.warning(f"The m/z range was too narrow so it was widened to {x_min:.2f}-{x_max:.2f}")

        # reshape object
        dt_obj = MobilogramObject(x, y)
        name = f"MZ_{x_min:.2f}-{x_max:.2f}"
        return name, dt_obj

    @staticmethod
    @check_os("win32")
    def get_waters_info(path: str):
        """Retrieves information about the file in question"""
        reader = WatersIMReader(path)
        info = dict(is_im=reader.is_im, n_scans=reader.n_scans(0), mz_range=reader.mz_range, cid=reader.info["trap_ce"])
        return info

    @staticmethod
    def load_text_spectrum_data(path):
        """Read mass spectrum data from text file"""
        reader = TextSpectrumReader(path)

        return reader.x, reader.y, reader.directory, reader.x_limits, reader.extension

    def load_text_mass_spectrum_document(self, path):
        """Read textual mass spectral data and create new document"""
        x, y, _, _, _ = self.load_text_spectrum_data(path)
        mz_obj = MassSpectrumObject(x, y)

        document = ENV.get_new_document("origami", path, data=dict(mz=mz_obj))
        return document

    @staticmethod
    def load_text_annotated_data(filename):
        """Read annotated data from text file"""
        reader = AnnotatedDataReader(filename)

        return reader.dataset_title, reader.data

    @staticmethod
    def load_text_heatmap_data(path):
        """Read heatmap data from text file"""
        reader = TextHeatmapReader(path)

        return IonHeatmapObject(reader.array, x=reader.x, y=reader.y, xy=reader.xy, yy=reader.yy)

    def load_text_heatmap_document(self, path):
        """Load heatmap data from text file and instantiate it as a document"""
        heatmap_obj = self.load_text_heatmap_data(path)
        document = ENV.get_new_document("origami", path, data=dict(heatmap=heatmap_obj))
        return document

    @staticmethod
    def load_mgf_data(path):
        """Read data from MGF file format"""
        t_start = time.time()
        reader = MGFReader(path)
        LOGGER.debug("Created MGF file reader. Started loading data...")

        data = reader.get_n_scans(MGF_N_SCANS)
        LOGGER.debug("Loaded MGF data in " + report_time(t_start))
        return reader, data

    def load_mgf_document(self, path):
        """Load mgf data and set inside ORIGAMI document"""
        # read data
        reader, data = self.load_mgf_data(path)

        # instantiate document
        document = ENV.get_new_document("mgf", path)
        # set data
        document.tandem_spectra = data
        document.add_reader("data_reader", reader)
        document.add_file_path("main", path)

        return document

    @staticmethod
    def load_mzml_data(path):
        """Read data from mzML file format"""
        t_start = time.time()
        reader = mzMLReader(path)
        LOGGER.debug("Created mzML file reader. Started loading data...")

        data = reader.get_n_scans(MZML_N_SCANS)
        LOGGER.debug("Loaded mzML data in " + report_time(t_start))
        return reader, data

    def load_mzml_document(self, path):
        """Load mzml data and set inside ORIGAMI document"""
        # read data
        reader, data = self.load_mzml_data(path)

        # instantiate document
        document = ENV.get_new_document("mzml", path)
        # set data
        document.tandem_spectra = data
        document.add_reader("data_reader", reader)
        document.add_file_path("main", path)

        return document

    @staticmethod
    @check_os("win32")
    def load_thermo_ms_data(path):
        """Load Thermo data"""
        from origami.readers.io_thermo_raw import ThermoRawReader

        t_start = time.time()
        reader = ThermoRawReader(path)
        LOGGER.debug("Created Thermo file reader. Started loading data...")

        # get average data
        chromatogram: ChromatogramObject = reader.get_tic()
        LOGGER.debug("Loaded TIC in " + report_time(t_start))

        mass_spectrum: MassSpectrumObject = reader.get_spectrum()
        LOGGER.debug("Loaded spectrum in " + report_time(t_start))

        # get mass spectra
        mass_spectra: Dict[MassSpectrumObject] = reader.get_spectrum_for_each_filter()
        chromatograms: Dict[ChromatogramObject] = reader.get_chromatogram_for_each_filter()

        data = {"mz": mass_spectrum, "rt": chromatogram, "mass_spectra": mass_spectra, "chromatograms": chromatograms}
        return reader, data

    @check_os("win32")
    def load_thermo_ms_document(self, path):
        """Load Thermo data and set in ORIGAMI document"""
        reader, data = self.load_thermo_ms_data(path)

        document = ENV.get_new_document("thermo", path, data=data)
        document.add_reader("data_reader", reader)
        document.add_file_path("main", path)

        return document

    def _parse_clipboard_stream(self, clip_stream):
        """Parse clipboard stream data"""
        data = []
        for t in clip_stream:
            line = t.split()
            try:
                data.append(list(map(float, line)))
            except (ValueError, TypeError):
                LOGGER.warning("Failed to convert mass range to dtype: float")

        if not data:
            return None

        # check data size
        sizes = []
        for _d in data:
            sizes.append(len(_d))

        if len(np.unique(sizes)) != 1:
            raise ValueError("Could not parse clipboard data")

        data = np.asarray(data)
        return data

    def load_clipboard_ms_document(self, path, clip_stream):
        """Load clipboard data and instantiate new document"""
        # process clipboard stream
        data = self._parse_clipboard_stream(clip_stream)
        if data is None:
            raise ValueError("Clipboard object was empty")

        mz_obj = MassSpectrumObject(data[:, 0], data[:, 1])
        title = os.path.basename(path)
        document = ENV.get_new_document("text", path, data=dict(mz=mz_obj), title=title)

        return document

    @staticmethod
    @check_os("win32")
    def load_waters_ms_data(path):
        """Load Waters mass spectrometry and chromatographic data"""
        t_start = time.time()
        reader = WatersRawReader(path)
        LOGGER.debug("Initialized Waters reader")

        mz_obj = reader.get_average_spectrum()
        LOGGER.debug("Loaded spectrum in " + report_time(t_start))

        rt_x, rt_y = reader.get_tic(0)
        LOGGER.debug("Loaded TIC in " + report_time(t_start))

        parameters = reader.get_inf_data()

        data = {
            "mz": mz_obj,
            "rt": ChromatogramObject(
                rt_x,
                rt_y,
                x_label="Time (min)",
                metadata=dict(scan_time=parameters["scan_time"]),
                extra_data=dict(x_min=rt_x),
            ),
            "parameters": parameters,
        }
        LOGGER.debug("Loaded data in " + report_time(t_start))
        return reader, data

    @check_os("win32")
    def load_waters_ms_document(self, path):
        """Load Waters data and set in ORIGAMI document"""
        reader, data = self.load_waters_ms_data(path)
        document = ENV.get_new_document("waters_ms", path, data=data)
        document.add_reader("data_reader", reader)
        document.add_file_path("main", path)

        return document

    @staticmethod
    @check_os("win32")
    def check_waters_im(path):
        """Checks whether dataset has ion mobility"""
        try:
            _ = WatersIMReader(path)
            return True
        except NoIonMobilityDatasetError:
            return False

    @check_os("win32")
    def load_waters_im_data(self, path: str):
        """Load Waters IM-MS data"""
        t_start = time.time()
        reader = WatersIMReader(path, temp_dir=CONFIG.temporary_data)
        LOGGER.debug("Initialized Waters reader")

        mz_obj: MassSpectrumObject = reader.extract_ms()
        LOGGER.debug("Loaded spectrum in " + report_time(t_start))

        rt_obj: ChromatogramObject = reader.extract_rt()
        LOGGER.debug("Loaded RT in " + report_time(t_start))

        dt_obj: MobilogramObject = reader.extract_dt()
        LOGGER.debug("Loaded DT in " + report_time(t_start))

        heatmap_obj: IonHeatmapObject = reader.extract_heatmap()
        LOGGER.debug("Loaded DT in " + report_time(t_start))

        mzdt_obj: MassSpectrumHeatmapObject = self.waters_im_extract_msdt(path, reader.mz_min, reader.mz_max)
        LOGGER.debug("Loaded MSDT in " + report_time(t_start))
        parameters = reader.get_inf_data()

        data = {
            "mz": mz_obj,
            "rt": rt_obj,
            "dt": dt_obj,
            "heatmap": heatmap_obj,
            "msdt": mzdt_obj,
            "parameters": parameters,
        }
        LOGGER.debug("Loaded data in " + report_time(t_start))
        return reader, data

    @check_os("win32")
    def load_waters_im_document(self, path: str):
        """Load Waters data and set in ORIGAMI document"""
        reader, data = self.load_waters_im_data(path)
        document = ENV.get_new_document("origami", path, data=data)
        document.add_reader("data_reader", reader)
        document.add_file_path("main", path)

        return document

    def load_lesa_document(self, path, filelist: List[FileItem], **proc_kwargs) -> DocumentStore:
        """Load Waters data and set in ORIGAMI document"""
        document = ENV.get_new_document("imaging", path)

        #         filelist = self.check_lesa_document(document, filelist, **proc_kwargs)
        data = self.load_multi_file_waters_data(filelist, **proc_kwargs)
        document = ENV.set_document(document, data=data)
        document.add_config("imaging", proc_kwargs)
        ImagingNormalizationProcessor(document)
        #         document.add_file_path("multi", filelist)

        return document

    def load_manual_document(self, path, filelist: List[FileItem], **proc_kwargs) -> DocumentStore:
        """Load Waters data and set in ORIGAMI document"""
        document = ENV.get_new_document("activation", path)

        filelist = self.check_lesa_document(document, filelist, **proc_kwargs)
        data = self.load_multi_file_waters_data(filelist, **proc_kwargs)
        document = ENV.set_document(document, data=data)
        document.add_config("activation", proc_kwargs)
        #         document.add_file_path("multi", filelist)

        return document

    #     def load_multi_file_waters_data_mt(self, filelist: List[FileItem], **proc_kwargs):
    #         from concurrent.futures import wait, ThreadPoolExecutor, ProcessPoolExecutor
    #         from origami.utils.utilities import as_chunks
    #
    #         """Load waters data using multiple cores"""
    #         executor = ProcessPoolExecutor(4)
    #
    #         futures = []
    #         for start, _filelist in as_chunks(filelist, 3):
    #             futures.append(executor.submit(_load_multi_file_waters_data, _filelist, **proc_kwargs))
    #
    #         done, notdone = wait(futures)
    #         if len(notdone) > 0:
    #             raise ValueError("Failed to execute action in multi-core manner")
    #
    #         mass_spectra, chromatograms, mobilograms, variables, parameters = {}, {}, {}, {}, {}
    #         for future in done:
    #             _mass_spectra, _chromatograms, _mobilograms, _variables, _parameters = future.result()
    #             mass_spectra.update(**_mass_spectra)
    #             chromatograms.update(**_chromatograms)
    #             mobilograms.update(**_mobilograms)
    #             variables.update(**_variables)
    #             if _parameters:
    #                 parameters = _parameters
    #
    #         data_out = dict(mass_spectra=mass_spectra, chromatograms=chromatograms, mobilograms=mobilograms)
    #         data_out.update(**self.finalize_multi_file_waters_data(mass_spectra, mobilograms, variables,
    #         **proc_kwargs))
    #         if parameters:
    #             data_out["parameters"] = parameters
    #
    #         return data_out

    @check_os("win32")
    def load_multi_file_waters_data(self, filelist: List[FileItem], **proc_kwargs):
        """Vendor agnostic LESA data load"""
        mass_spectra, chromatograms, mobilograms, msdts, variables, parameters = _load_multi_file_waters_data(
            filelist, **proc_kwargs
        )
        data_out = dict(mass_spectra=mass_spectra, chromatograms=chromatograms, mobilograms=mobilograms, msdts=msdts)
        data_out.update(**self.finalize_multi_file_waters_data(mass_spectra, mobilograms, variables, **proc_kwargs))

        if parameters:
            data_out["parameters"] = parameters

        return data_out

    @staticmethod
    def finalize_multi_file_waters_data(
        mass_spectra: Dict = None, mobilograms: Dict = None, variables: Dict = None, **proc_kwargs
    ):
        """Finalize multi-file document by generating average spectra, heatmaps, etc"""
        data_out = dict()

        # average mass spectrum
        if mass_spectra:
            mz_obj = MassSpectrumGroup(mass_spectra).mean(**deepcopy(proc_kwargs))
            data_out["mz"] = mz_obj

        # stitch heatmap together based input variables
        if mobilograms and variables:
            variables = list(variables.values())
            spectra = list(mobilograms.values())
            heatmap_obj = StitchIonHeatmapObject(spectra, variables)
            data_out["heatmap"] = heatmap_obj

        return data_out

    @staticmethod
    def check_lesa_document(document: DocumentStore, filelist: List[FileItem], **proc_kwargs) -> List[FileItem]:
        """Check whether the dataset already has some spectral data"""

        def compare_parameters():
            """Compare processing parameters"""
            for key in ["linearize", "baseline", "im_on"]:
                if _proc_kwargs.get(key, None) != proc_kwargs[key]:
                    return False
                return True

        def remove_item():
            """Remove item that has already been processed"""
            for file_info in filelist:
                if file_info.path == path:
                    filelist.remove(file_info)
                    LOGGER.debug(
                        f"File with path `{path}` has been extracted before with the same pre-processing"
                        f" parameters - not extracting it again."
                    )
                    break

        metadata = document.get_config("imaging", None)

        if metadata is None:
            return filelist

        # check data of the each spectrum
        mass_spectra = document["MassSpectra"]
        for name in mass_spectra:
            obj = mass_spectra[name]
            if "preprocessing" not in obj.attrs or "file_info" not in obj.attrs:
                continue

            _proc_kwargs = obj.attrs["preprocessing"]
            path = obj.attrs["file_info"]["path"]
            if compare_parameters():
                remove_item()

        return filelist


def _load_multi_file_waters_data(filelist: List[FileItem], **proc_kwargs):
    t_start = time.time()
    n_items = len(filelist)

    # iterate over all selected files
    mass_spectra, chromatograms, mobilograms, msdts, variables, parameters = {}, {}, {}, {}, {}, {}
    for file_id, file_info in enumerate(filelist):
        # create item name
        __, filename = os.path.split(file_info.path)
        spectrum_name = f"{file_info.variable}={filename}"

        # get item data
        variables[spectrum_name] = file_info.variable
        mz_obj, rt_obj, dt_obj, msdt_obj, parameters = _load_waters_data_chunk(file_info, **deepcopy(proc_kwargs))
        mass_spectra[spectrum_name] = mz_obj
        chromatograms[spectrum_name] = rt_obj
        if dt_obj is not None:
            mobilograms[spectrum_name] = dt_obj
        if msdt_obj is not None:
            msdts[spectrum_name] = msdt_obj
        LOGGER.debug(time_loop(t_start, file_id, n_items))
    return mass_spectra, chromatograms, mobilograms, msdts, variables, parameters


def _load_waters_data_chunk(file_info: FileItem, **proc_kwargs):
    """Load waters data for single chunk"""
    dt_obj, msdt_obj = None, None
    reader = WatersIMReader(file_info.path, silent=True)

    # get parameters
    parameters = reader.get_inf_data()

    # unpack processing kwargs
    mz_start, mz_end = file_info.mz_range
    scan_start, scan_end = file_info.scan_range

    # get mass spectrum
    mz_obj = reader.get_spectrum(scan_start, scan_end)

    # linearization is necessary
    lin_kwargs = proc_kwargs
    if "linearize" in proc_kwargs:
        lin_kwargs = proc_kwargs["linearize"]
    mz_obj.linearize(**lin_kwargs)

    # but baseline correction is not
    baseline_kwargs = proc_kwargs
    if "baseline" in proc_kwargs:
        baseline_kwargs = proc_kwargs["baseline"]
    if baseline_kwargs.get("correction", False):
        mz_obj.baseline(**baseline_kwargs)

    mz_obj.set_metadata(dict(preprocessing=proc_kwargs, file_info=dict(file_info._asdict())))  # noqa

    # get chromatogram
    rt_start, rt_end = reader.convert_scan_to_min([scan_start, scan_end])
    rt_obj = reader.extract_rt(rt_start=rt_start, rt_end=rt_end, mz_start=mz_start, mz_end=mz_end)

    # get mobilogram
    if file_info.im_on:
        dt_obj = reader.extract_dt(rt_start=rt_start, rt_end=rt_end, mz_start=mz_start, mz_end=mz_end)

    # get msdt
    if file_info.im_on:
        msdt_kwargs = dict(x_min=mz_start, x_max=mz_end, bin_size=1)
        if "msdt" in proc_kwargs:
            msdt_kwargs = proc_kwargs["msdt"]

        msdt_obj = reader.extract_msdt(
            rt_start=rt_start,
            rt_end=rt_end,
            mz_start=msdt_kwargs["x_min"],
            mz_end=msdt_kwargs["x_max"],
            mz_bin_size=msdt_kwargs["bin_size"],
        )
        msdt_obj.set_metadata(dict(file_info=dict(file_info._asdict())))

    return mz_obj, rt_obj, dt_obj, msdt_obj, parameters
