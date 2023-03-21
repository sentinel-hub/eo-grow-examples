<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis minScale="1e+08" maxScale="0" hasScaleBasedVisibilityFlag="0" version="3.22.12-Białowieża" styleCategories="AllStyleCategories">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" fetchMode="0" mode="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <customproperties>
    <Option type="Map">
      <Option type="bool" name="WMSBackgroundLayer" value="false"/>
      <Option type="bool" name="WMSPublishDataSourceUrl" value="false"/>
      <Option type="int" name="embeddedWidgets/count" value="0"/>
      <Option type="QString" name="identify/format" value="Value"/>
    </Option>
  </customproperties>
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option type="QString" name="name" value=""/>
      <Option name="properties"/>
      <Option type="QString" name="type" value="collection"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling enabled="false" maxOversampling="2" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer alphaBand="-1" nodataColor="" type="paletted" opacity="1" band="1">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <colorPalette>
        <paletteEntry label="forest" alpha="255" color="#054907" value="1"/>
        <paletteEntry label="grass" alpha="255" color="#a7df8a" value="2"/>
        <paletteEntry label="farmland" alpha="255" color="#39b030" value="3"/>
        <paletteEntry label="bare soil" alpha="255" color="#9f7f3a" value="4"/>
        <paletteEntry label="sand" alpha="255" color="#e6daa6" value="5"/>
        <paletteEntry label="built-up" alpha="255" color="#ca0020" value="6"/>
        <paletteEntry label="permanent water" alpha="255" color="#069af3" value="7"/>
        <paletteEntry label="intermittent water" alpha="255" color="#95d0fc" value="8"/>
        <paletteEntry label="ice and snow" alpha="255" color="#404040" value="9"/>
      </colorPalette>
      <colorramp type="randomcolors" name="[source]">
        <Option/>
      </colorramp>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation colorizeOn="0" invertColors="0" saturation="-12" grayscaleMode="0" colorizeRed="255" colorizeGreen="128" colorizeStrength="100" colorizeBlue="128"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
