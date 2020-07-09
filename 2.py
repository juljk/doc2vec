import numpy as np
from PIL import Image
from skimage import color
from skimage.feature import hog

from pelops.features.feature_producer import FeatureProducer


class HOGFeatureProducer(FeatureProducer):

    def __init__(self, chip_producer, image_size=(224,224), cells=(16, 16), orientations=8, histogram_bins_per_channel=256):
        self.image_size = image_size
        self.cells = cells
        self.orientations = orientations
        self.histogram_bins_per_channel = histogram_bins_per_channel
        super().__init__(chip_producer)

    def produce_features(self, chip):
        """Takes a chip object and returns a feature vector of size
        self.feat_size. """
        img = self.get_image(chip)
        img = img.resize(self.image_size, Image.BICUBIC)
        img_x, img_y = img.size

        # Calculate histogram of each channel
        channels = img.split()
        hist_features = np.full(shape=3 * self.histogram_bins_per_channel, fill_value=-1)

        # We expect RGB images. If something else is passed warn the user and
        # continue.
        if len(channels) < 3:
            print("Non-RBG image! Vector will be padded with -1!")
        if len(channels) > 3:
            print("Non-RBG image! Channels beyond the first three will be ignored!")
            channels = channel[:3]
