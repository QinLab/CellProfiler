"""crop.py - crop or mask an image

CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Developed by the Broad Institute
Copyright 2003-2009

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
"""
__version__="$Revision$"

import math
import numpy as np
import sys

import cellprofiler.cpimage as cpi
import cellprofiler.settings as cps
import cellprofiler.cpmodule as cpm
import cellprofiler.gui.cpfigure as cpf
import cellprofiler.preferences as cpprefs

SH_ELLIPSE = "Ellipse"
SH_RECTANGLE = "Rectangle"
SH_IMAGE = "Image"
SH_OBJECTS = "Objects"
SH_CROPPING = "Cropping"
CM_COORDINATES = "Coordinates"
CM_MOUSE = "Mouse"
IO_INDIVIDUALLY = "Individually"
IO_FIRST = "First"
RM_NO = "No"
RM_EDGES = "Edges"
RM_ALL = "All"
OFF_IMAGE_NAME              = 0
OFF_CROPPED_IMAGE_NAME      = 1
OFF_SHAPE                   = 2
OFF_CROP_METHOD             = 3
OFF_INDIVIDUAL_OR_ONCE      = 4
OFF_HORIZONTAL_LIMITS       = 5
OFF_VERTICAL_LIMITS         = 6
OFF_CENTER                  = 7
OFF_X_RADIUS                = 8
OFF_Y_RADIUS                = 9
OFF_PLATE_FIX               = 10
OFF_REMOVE_ROWS_AND_COLUMNS = 11
OFF_IMAGE_MASK_SOURCE       = 12
OFF_CROPPING_MASK_SOURCE    = 13

class Crop(cpm.CPModule):
    """% SHORT DESCRIPTION:
Crops images into a rectangle, ellipse, an arbitrary shape provided by
the user, a shape identified by an identify module, or a shape used at a
previous step in the pipeline on another image.
*************************************************************************

Keep in mind that cropping changes the size of your images, which may
have unexpected consequences. For example, identifying objects in a
cropped image and then trying to measure their intensity in the
*original* image will not work because the two images are not the same
size.

Features measured:
AreaRetainedAfterCropping
OriginalImageArea


Settings:

Shape:
Rectangle - self-explanatory.
Ellipse - self-explanatory.
Image - a binary image
Objects - the labeled objects output by an Identify module
Cropping - the cropping generated by a previous cropping module
A choice box with available images appears if you choose "Image"
* To crop based on an object identified in a previous module, select "Objects"
  and choose the name of that identified object. Please see PlateFix for 
  information on cropping based on previously identified plates.
* To crop into an arbitrary shape you define, choose "Image" and
  use the LoadSingleImage module to load a black and white image 
  (that you have already prepared) from a file. 
  If you have created this image in an image program such as
  Photoshop, this binary image should contain only the values 0 and 255,
  with zeros (black) for the parts you want to remove and 255 (white) for
  the parts you want to retain. Or, you may have previously generated a
  binary image using this module (e.g. using the ellipse option) and saved
  it using the SaveImages module (see Special note on saving images below).
  In any case, the image must be the exact same starting size as your image
  and should contain a contiguous block of white pixels, because keep in
  mind that the cropping module will remove rows and columns that are
  completely blank.
A choice box with available images appears if you choose "Cropping". The
images in this box are ones that were generated by previous Crop modules.
This crop module will use the same cropping as was used to generate the image
you choose.

Coordinate or mouse: For ellipse, you will be asked to click five or more
points to define an ellipse around the part of the image you want to
analyze.  Keep in mind that the more points you click, the longer it will
take to calculate the ellipse shape. For rectangle, you can click as many
points as you like that are in the interior of the region you wish to
retain.

PlateFix: To be used only when cropping based on previously identified
objects. When attempting to crop based on a previously identified object
(such as a yeast plate), sometimes the identified plate does not have
precisely straight edges - there might be a tiny, almost unnoticeable
'appendage' sticking out of the plate.  Without plate fix, the crop
module would not crop the image tightly enough - it would include enough
of the image to retain even the tiny appendage, so there would be a lot
of blank space around the plate. This can cause problems with later
modules (especially IlluminationCorrection). PlateFix takes the
identified object and crops to exclude any minor appendages (technically,
any horizontal or vertical line where the object covers less than 50% of
the image). It also sets pixels around the edge of the object (for
regions > 50% but less than 100%) that otherwise would be zero to the
background pixel value of your image thus avoiding the problems with
other modules. Important note >> PlateFix uses the coordinates
entered in the boxes normally used for rectangle cropping (Top, Left) and
(Bottom, Right) to tighten the edges around your identified plate. This
is done because in the majority of plate identifications you do not want
to include the sides of the plate. If you would like the entire plate to
be shown, you should enter 1:end for both coordinates. If you would like
to crop 80 pixels from each edge of the plate, you could enter 80:end-80
for (Top, Left) and (Bottom, Right).

Do you want to remove rows and columns that lack objects?
The options are:
* No - leave the image the same size
* Edges - crop the image so that its top, bottom, left and right are at
          the first nonblank pixel for that edge
* All - remove any row or column of all-blank pixels, even from the
        internal portion of the image

Special note on saving images: See the help for the SaveImages module.
You can save the cropping shape that you have used (e.g. an ellipse
you drew), so that in future analyses you can use the File option. To do
this, choose to save either the mask or cropping in SaveImages for the image 
generated by this module.
    """
    variable_revision_number = 2
    category = "Image Processing"
    
    def create_settings(self):
        self.module_name = "Crop"
        self.image_name = cps.ImageNameSubscriber("What did you call the image to be cropped?","None")
        self.cropped_image_name = cps.CroppingNameProvider("What do you want to call the cropped image?","CropBlue")
        self.shape=cps.Choice("Into which shape would you like to crop?",
                              [SH_ELLIPSE, SH_RECTANGLE, SH_IMAGE,
                               SH_OBJECTS, SH_CROPPING],
                              SH_ELLIPSE)
        self.crop_method = cps.Choice("Would you like to crop by typing in pixel coordinates or clicking with the mouse?",
                                      [CM_COORDINATES, CM_MOUSE], CM_COORDINATES)
        self.individual_or_once = cps.Choice("Should the cropping pattern in the first image cycle be applied to all subsequent image cycles (First option) or should each image cycle be cropped individually?",
                                             [IO_INDIVIDUALLY, IO_FIRST],
                                             IO_INDIVIDUALLY)
        self.horizontal_limits = cps.IntegerOrUnboundedRange("Specify the left and right positions for the bounding rectangle:",
                                                             minval=0)
        self.vertical_limits = cps.IntegerOrUnboundedRange("Specify the top and bottom positions for the bounding rectangle:",
                                                           minval=0)
        self.ellipse_center = cps.Coordinates("What is the center pixel position of the ellipse?",(500,500))
        self.ellipse_x_radius = cps.Integer("What is the radius of the ellipse in the X direction?",400)
        self.ellipse_y_radius = cps.Integer("What is the radius of the ellipse in the Y direction?",200)
        self.image_mask_source = cps.ImageNameSubscriber("What is the name of the image to use as a cropping mask?","None")
        self.cropping_mask_source = cps.CroppingNameSubscriber("What is the name of the image with the associated cropping mask?","None")
        self.objects_source = cps.ObjectNameSubscriber("What is the name of the objects to use as a cropping mask?","None")
        self.use_plate_fix = cps.Binary("Do you want to use Plate Fix?",False)
        self.remove_rows_and_columns = cps.Choice("Do you want to remove rows and columns that lack objects?",
                                                  [RM_NO, RM_EDGES, RM_ALL],
                                                  RM_NO)
        #
        # If the user chooses "First" for individual_or_once, then we
        # save the cropping and crop mask here for subsequent images
        #
        self.__first_cropping = None
        self.__first_crop_mask = None
    
    def settings(self):
        return [self.image_name, self.cropped_image_name, self.shape,
                self.crop_method, self.individual_or_once,
                self.horizontal_limits, self.vertical_limits,
                self.ellipse_center, self.ellipse_x_radius, 
                self.ellipse_y_radius, self.use_plate_fix,
                self.remove_rows_and_columns, self.image_mask_source,
                self.cropping_mask_source, self.objects_source]
    
    def backwards_compatibilize(self,setting_values,variable_revision_number,
                               module_name,from_matlab):
        if from_matlab and variable_revision_number==4:
            # Added OFF_REMOVE_ROWS_AND_COLUMNS
            new_setting_values = list(setting_values)
            new_setting_values.append(cps.NO)
            variable_revision_number = 5
        if from_matlab and variable_revision_number==5:
            # added image mask source, cropping mask source and reworked
            # the shape to add SH_IMAGE and SH_CROPPING
            new_setting_values = list(setting_values)
            new_setting_values.extend(["None","None","None"])
            shape = setting_values[OFF_SHAPE]
            if shape not in (SH_ELLIPSE, SH_RECTANGLE):
                # the "shape" is the name of some image file. If it
                # starts with Cropping, then it's the crop mask of
                # some other image
                if shape.startswith('Cropping'):
                    new_setting_values[OFF_CROPPING_MASK_SOURCE] =\
                        shape[len('Cropping'):]
                    new_setting_values[OFF_SHAPE] = SH_CROPPING
                else:
                    new_setting_values[OFF_IMAGE_MASK_SOURCE] = shape
                    new_setting_values[OFF_SHAPE] = SH_IMAGE
            setting_values = new_setting_values
            variable_revision_number = 2
            from_matlab = False
        
        if (not from_matlab) and variable_revision_number == 1:
            # Added ability to crop objects
            new_setting_values = list(setting_values)
            new_setting_values.append("None")
            variable_revision_number = 2
            
        return setting_values, variable_revision_number, from_matlab
    
    def visible_settings(self):
        result = [self.image_name, self.cropped_image_name, self.shape]
        if self.shape.value in ( SH_RECTANGLE, SH_ELLIPSE):
            result += [self.crop_method, self.individual_or_once]
            if (self.crop_method == CM_COORDINATES):
                if self.shape == SH_RECTANGLE:
                    result += [self.horizontal_limits, self.vertical_limits]
                elif self.shape == SH_ELLIPSE:
                    result += [self.ellipse_center, self.ellipse_x_radius,
                               self.ellipse_y_radius]
        elif self.shape == SH_IMAGE:
            result += [self.image_mask_source, self.use_plate_fix]
            if self.use_plate_fix.value:
                result += [self.horizontal_limits, self.vertical_limits]
        elif self.shape == SH_CROPPING:
            result.append(self.cropping_mask_source)
        elif self.shape == SH_OBJECTS:
            result.append(self.objects_source)
        else:
            raise NotImplementedError("Unimplemented shape type: %s"%(self.shape.value))
        result += [self.remove_rows_and_columns]
        return result
   
    def run(self,workspace):
        orig_image = workspace.image_set.get_image(self.image_name.value)
        recalculate_flag = (self.individual_or_once == IO_INDIVIDUALLY or
                            workspace.image_set.number == 0)
        save_flag = (self.individual_or_once == IO_FIRST and
                     workspace.image_set.number == 0)
        if not recalculate_flag:
            if self.__first_cropping.shape != orig_image.pixel_data.shape[:2]:
                recalculate_flag = True
                sys.stderr.write("""Image, "%s", size changed from %s to %s during cycle %d, recalculating"""%
                                 (self.image_name.value, 
                                  str(self.__first_cropping.shape),
                                  str(orig_image.pixel_data.shape[:2]),
                                  workspace.image_set.number+1))
        mask = None # calculate the mask after cropping unless set below
        cropping = None
        masking_objects = None
        if not recalculate_flag:
            cropping = self.__first_cropping
            mask = self.__first_crop_mask
        elif self.shape == SH_CROPPING:
            cropping_image = workspace.image_set.get_image(self.cropping_mask_source.value)
            cropping = cropping_image.crop_mask
        elif self.shape == SH_IMAGE:
            source_image = workspace.image_set.get_image\
                (self.image_mask_source.value).pixel_data
            if self.use_plate_fix.value:
                source_image = self.plate_fixup(source_image)
            cropping = source_image > 0
        elif self.shape == SH_OBJECTS:
            masking_objects = workspace.get_objects(self.objects_source.value)
            cropping = masking_objects.segmented > 0
        elif self.crop_method == CM_MOUSE:
            cropping = self.ui_crop(workspace,orig_image)
        elif self.shape == SH_ELLIPSE:
            cropping = self.get_ellipse_cropping(workspace,orig_image)
        elif self.shape == SH_RECTANGLE:
            cropping = self.get_rectangle_cropping(workspace,orig_image)
        if self.remove_rows_and_columns == RM_NO:
            cropped_pixel_data = orig_image.pixel_data.copy()
            cropped_pixel_data[np.logical_not(cropping)] = 0
            if mask == None:
                mask = cropping
        else:
            internal_cropping = self.remove_rows_and_columns == RM_ALL
            cropped_pixel_data = cpi.crop_image(orig_image.pixel_data,
                                                cropping,
                                                internal_cropping)
            if mask == None:
                mask = cpi.crop_image(cropping, cropping, internal_cropping)
            cropped_pixel_data[np.logical_not(mask)] = 0
        if self.shape == SH_OBJECTS:
            # Special handling for objects - masked objects instead of
            # mask and crop mask
            output_image = cpi.Image(image=cropped_pixel_data,
                                     masking_objects = masking_objects,
                                     parent_image = orig_image)
        else:
            output_image=cpi.Image(image=cropped_pixel_data,
                                   mask=mask,
                                   parent_image = orig_image,
                                   crop_mask = cropping)
        #
        # Display the image
        #
        if workspace.frame != None:
            window_name = "CellProfiler(%s:%d)"%(self.module_name,self.module_num)
            my_frame=workspace.create_or_find_figure(
                        title="Crop image #%d"%(self.module_num), 
                        window_name=window_name, subplots=(2,1))
            
            title = "Original: %s, cycle # %d"%(self.image_name.value,
                                      workspace.image_set.number+1)
            my_frame.subplot_imshow_grayscale(0,0,orig_image.pixel_data,title)
            my_frame.subplot_imshow_bw(1,0,cropped_pixel_data,
                                       self.cropped_image_name.value)
        if save_flag:
            self.__first_crop_mask = mask
            self.__first_cropping = cropping
        #
        # Save the image / cropping / mask
        #
        workspace.image_set.add(self.cropped_image_name.value, output_image)
        #
        # Save the old and new image sizes
        #
        pixel_area = cpprefs.get_pixel_size() ** 2
        original_image_area = (np.product(orig_image.pixel_data.shape[:2]) *
                               pixel_area)
        area_retained_after_cropping = np.sum(cropping) * pixel_area
        feature = 'Crop_AreaRetainedAfterCropping_%s'%(self.cropped_image_name.value)
        m = workspace.measurements
        m.add_measurement('Image', feature,
                          np.array([area_retained_after_cropping]))
        feature = 'Crop_OriginalImageArea_%s'%(self.cropped_image_name.value)
        m.add_measurement('Image', feature,
                          np.array([original_image_area]))
                                            
    
    def ui_crop(self, workspace,orig_image):
        """Crop into a rectangle or ellipse, guided by UI"""
        raise NotImplementedError("Cropping using the mouse has not been implemented")
    
    def get_ellipse_cropping(self, workspace,orig_image):
        """Crop into an ellipse using user-specified coordinates"""
        pixel_data = orig_image.pixel_data
        x_max = pixel_data.shape[1]
        y_max = pixel_data.shape[0]
        x_center = self.ellipse_center.x
        y_center = self.ellipse_center.y
        x_radius = self.ellipse_x_radius.value
        y_radius = self.ellipse_y_radius.value
        if x_radius > y_radius:
            dist_x = math.sqrt(x_radius**2-y_radius**2)
            dist_y = 0
            major_radius = x_radius
        else:
            dist_x = 0
            dist_y = math.sqrt(y_radius**2-x_radius**2)
            major_radius = y_radius
        
        focus_1_x,focus_1_y = (x_center-dist_x,y_center-dist_y)
        focus_2_x,focus_2_y = (x_center+dist_x,y_center+dist_y)
        y,x = np.mgrid[0:y_max,0:x_max]
        d1 = np.sqrt((x-focus_1_x)**2+(y-focus_1_y)**2)
        d2 = np.sqrt((x-focus_2_x)**2+(y-focus_2_y)**2)
        cropping = d1+d2 <= major_radius*2
        return cropping
    
    def get_rectangle_cropping(self, workspace,orig_image):
        """Crop into a rectangle using user-specified coordinates"""
        cropping = np.ones(orig_image.pixel_data.shape,bool)
        if not self.horizontal_limits.unbounded_min:
            cropping[:,:self.horizontal_limits.min]=False
        if not self.horizontal_limits.unbounded_max:
            cropping[:,self.horizontal_limits.max:]=False
        if not self.vertical_limits.unbounded_min:
            cropping[:self.vertical_limits.min,:]=False
        if not self.vertical_limits.unbounded_max:
            cropping[self.vertical_limits.max:,:]=False
        return cropping
        
    def plate_fixup(self,pixel_data):
        """Fix up the cropping image based on the plate fixup rules
        
        The rules:
        * Trim rows and columns off of the edges if less than 50%
        * Use the horizontal and vertical trim to trim the image further
        """ 
        pixel_data = pixel_data.copy()
        i_histogram = pixel_data.sum(axis=1)
        i_cumsum    = np.cumsum(i_histogram > pixel_data.shape[0]/2)
        j_histogram = pixel_data.sum(axis=0)
        j_cumsum    = np.cumsum(j_histogram > pixel_data.shape[1]/2)
        i_first     = np.argwhere(i_cumsum==1)[0]
        i_last      = np.argwhere(i_cumsum==i_cumsum.max())[0]
        i_end       = i_last+1
        j_first     = np.argwhere(j_cumsum==1)[0]
        j_last      = np.argwhere(j_cumsum==j_cumsum.max())[0]
        j_end       = j_last+1
        if not self.horizontal_limits.unbounded_min:
            j_first = max(j_first,self.horizontal_limits.min)
        if not self.horizontal_limits.unbounded_max:
            j_end = min(j_end, self.horizontal_limits.max)
        if not self.vertical_limits.unbounded_min:
            i_first = max(i_first,self.vertical_limits.min)
        if not self.vertical_limits.unbounded_max:
            i_end = min(i_end, self.vertical_limits.max)
        if i_first > 0:
            pixel_data[:i_first,:] = 0
        if i_end < pixel_data.shape[0]:
            pixel_data[i_end:,:] = 0
        if j_first > 0:
            pixel_data[:,:j_first] = 0
        if j_end < pixel_data.shape[1]:
            pixel_data[:,j_end:] = 0
        return pixel_data
        