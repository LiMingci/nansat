#-------------------------------------------------------------------------------
# Name:         mapper_CSKS.py
# Purpose:      Mapper for Cosmo-Skymed SAR data
#
# Author:       Morten Wergeland Hansen
# Modified:	Morten Wergeland Hansen
#
# Created:	17.10.2012
# Last modified:01.11.2012 16:43
# Copyright:    (c) NERSC
# License:      
#-------------------------------------------------------------------------------

from dateutil.parser import parse
from struct import unpack
from vrt import VRT, Geolocation
import numpy as np
import os
import gdal, osr

class Mapper(VRT):
    ''' VRT with mapping of WKV for Cosmo-Skymed '''

    def __init__(self, fileName, gdalDataset, gdalMetadata ):
        ''' Create CSKS VRT '''

        # Let it be possible to choose these later
        band='S01'
        res='SBI'

        if fileName[0:4] != "CSKS":
            raise AttributeError("COSMO-SKYMED BAD MAPPER")

        # Get sub-datasets
        subDatasets = gdalDataset.GetSubDatasets()

        # Get file names from dataset or subdataset
        if subDatasets.__len__()==1:
            fileNames = [fileName]
        else:
            fileNames = [f[0] for f in subDatasets]

        # Get rid of the "unwanted" datasets
        for i,elem in enumerate(fileNames):
            band_number = i
            if fileNames[i][-3:]!=res:
                fileNames.pop(i)
            if fileNames[i][-7:-4]!=band:
                fileNames.pop(i)
        
        subDataset = gdal.Open(fileNames[0])


        # Get coordinates
        bottom_left_lon = float(gdalMetadata['Estimated_Bottom_Left_Geodetic_Coordinates'].split(' ')[1])
        bottom_left_lat = float(gdalMetadata['Estimated_Bottom_Left_Geodetic_Coordinates'].split(' ')[0])
        bottom_right_lon = float(gdalMetadata['Estimated_Bottom_Right_Geodetic_Coordinates'].split(' ')[1])
        bottom_right_lat = float(gdalMetadata['Estimated_Bottom_Right_Geodetic_Coordinates'].split(' ')[0])
        top_left_lon = float(gdalMetadata['Estimated_Top_Left_Geodetic_Coordinates'].split(' ')[1])
        top_left_lat = float(gdalMetadata['Estimated_Top_Left_Geodetic_Coordinates'].split(' ')[0])
        top_right_lon = float(gdalMetadata['Estimated_Top_Right_Geodetic_Coordinates'].split(' ')[1])
        top_right_lat = float(gdalMetadata['Estimated_Top_Right_Geodetic_Coordinates'].split(' ')[0])
        center_lon = float(gdalMetadata['Scene_Centre_Geodetic_Coordinates'].split(' ')[1])
        center_lat = float(gdalMetadata['Scene_Centre_Geodetic_Coordinates'].split(' ')[0])

        # generate list of GCPs
        gcps = []
        # create GCP with X,Y,Z(?),pixel,line from lat/lon matrices
        gcp = gdal.GCP(float(bottom_left_lon), float(bottom_left_lat), 0, 0, 0)
        gcps.append( gcp )
        #self.logger.debug('%d %d %d %f %f', 0, gcp.GCPPixel, gcp.GCPLine, gcp.GCPX, gcp.GCPY)
        gcp = gdal.GCP(float(bottom_right_lon), float(bottom_right_lat), 0, subDataset.RasterXSize, 0)
        gcps.append( gcp )
        #self.logger.debug('%d %d %d %f %f', 1, gcp.GCPPixel, gcp.GCPLine, gcp.GCPX, gcp.GCPY)
        gcp = gdal.GCP(float(top_left_lon), float(top_left_lat), 0, 0, subDataset.RasterYSize)
        gcps.append( gcp )
        #self.logger.debug('%d %d %d %f %f', 2, gcp.GCPPixel, gcp.GCPLine, gcp.GCPX, gcp.GCPY)
        gcp = gdal.GCP(float(top_right_lon), float(top_right_lat), 
                0, subDataset.RasterXSize, subDataset.RasterYSize)
        gcps.append( gcp )
        #self.logger.debug('%d %d %d %f %f', 3, gcp.GCPPixel, gcp.GCPLine, gcp.GCPX, gcp.GCPY)
        gcp = gdal.GCP(float(center_lon), float(center_lat),
                0, int(np.round(subDataset.RasterXSize/2.)), 
                int(round(subDataset.RasterYSize/2.)))
        gcps.append( gcp )
        #self.logger.debug('%d %d %d %f %f', 4, gcp.GCPPixel, gcp.GCPLine, gcp.GCPX, gcp.GCPY)
        
        # append GCPs and lat/lon projection to the vsiDataset
        latlongSRS = osr.SpatialReference()
        latlongSRS.ImportFromProj4("+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs")
        latlongSRSWKT = latlongSRS.ExportToWkt()
        
        # create empty VRT dataset with geolocation only
        VRT.__init__(self, srcRasterXSize=subDataset.RasterXSize,
                srcRasterYSize=subDataset.RasterYSize,
                srcGCPs=gcps,
                srcGCPProjection=latlongSRSWKT)

        print self.fileName
        #print fileNames[0]

        # Add real and imaginary raw counts as bands
        metaDict = [
                {'src': {'SourceFilename': fileNames[0], 'SourceBand': 1, 
                    'DataType': gdal.GDT_Int16}, 
                    'dst': {'dataType': gdal.GDT_Float32, 
                        'name': 'reRawCounts_%s' % gdalMetadata[band+'_Polarisation']}}]
        metaDict.append(
                {'src': {'SourceFilename': fileNames[0], 'SourceBand': 2,
                    'DataType': gdal.GDT_Int16},
                    'dst': {'dataType': gdal.GDT_Float32,
                        'name': 'imRawCounts_%s' % gdalMetadata[band+'_Polarisation'] }} )

        #metaDict.append({'src': [{'SourceFilename': fileNames[0], 
        #            'DataType': gdal.GDT_Int16,
        #            'SourceBand': 1}, 
        #                { 'SourceFilename': fileNames[0], 
        #                    'DataType': gdal.GDT_Int16, 
        #                    'SourceBand': 2}],
        #                'dst': {'wkv': 'surface_backwards_scattering_coefficient_of_radar_wave',
        #                    'PixelFunctionType': 'RawcountsToSigma0_CosmoSkymed_SBI',
        #                    'polarisation': gdalMetadata[band+'_Polarisation'],
        #                    'name': 'sigma0_%s' % gdalMetadata[band+'_Polarisation'],
        #                    'SatelliteID': gdalMetadata['Satellite_ID'],
        #                    'dataType': gdal.GDT_Float32}
        #                })

        # add band with metadata and corresponding values to the empty VRT
        self._create_bands(metaDict)

        # Calculate sigma0 scaling factor
        Rref = float(gdalMetadata['Reference_Slant_Range'])
        Rexp = float(gdalMetadata['Reference_Slant_Range_Exponent'])
        alphaRef = float(gdalMetadata['Reference_Incidence_Angle'])
        F=float(gdalMetadata['Rescaling_Factor'])
        K=float(gdalMetadata[band+'_Calibration_Constant'])
        Ftot = Rref**(2.*Rexp)
        Ftot *=np.sin(alphaRef*np.pi/180.0)
        Ftot /=F**2.
        Ftot /=K

        #print 'Reference slant range: '+str(Rref)
        #print 'RSR Exponent: '+str(Rexp)
        #print 'Reference Incidence Angle: '+str(alphaRef)
        #print 'Rescaling Factor: '+str(F)
        #print 'Calibration constant '+band+' channel: '+str(K)
        #print 'Total rescaling factor: '+str(Ftot)

        #metaDict.append(
        #        {'src': [{'SourceFilename': self.fileName, 'DataType':
        #            gdal.GDT_Float32, 'SourceBand': 1, 'ScaleRatio': Ftot}, 
        #                { 'SourceFilename': self.fileName, 'dataType':
        #                    gdal.GDT_Float32, 'SourceBand': 2}],
        src = [{'SourceFilename': self.fileName, 
                    'DataType': gdal.GDT_Float32,
                    'SourceBand': 1, 'ScaleRatio': np.sqrt(Ftot)}, 
                        { 'SourceFilename': self.fileName, 
                            'DataType': gdal.GDT_Float32, 
                            'SourceBand': 2, 'ScaleRatio': np.sqrt(Ftot)}]
        #src = [{'SourceFilename': fileNames[0], 
        #            'DataType': gdal.GDT_Int16,
        #            'SourceBand': 1}, 
        #                { 'SourceFilename': fileNames[0], 
        #                    'DataType': gdal.GDT_Int16, 
        #                    'SourceBand': 2}]
        dst = {'wkv': 
                'surface_backwards_scattering_coefficient_of_radar_wave',
                'PixelFunctionType': 'RawcountsToSigma0_CosmoSkymed_SBI',
                'polarisation': gdalMetadata[band+'_Polarisation'],
                'name': 'sigma0_%s' % gdalMetadata[band+'_Polarisation'],
                'SatelliteID': gdalMetadata['Satellite_ID'],
                'dataType': gdal.GDT_Float32}
                #'pass': gdalMetadata[''] - I can't find this in the metadata...

        self._create_band(src,dst)

