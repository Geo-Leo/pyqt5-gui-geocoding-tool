import pandas as pd
import geopandas as gpd   
import numpy as np     
import folium, multiprocessing, csv, os, openpyxl, time, requests, io
from geocodio import GeocodioClient


# Global variables
cpuNum = multiprocessing.cpu_count() - 2  # Determine number of cores to use
workspace = os.getcwd()

# Function to geocode addresses from input table
def geocodeAddresses(filename, outputShp, varList, geocoder, geocodedExport=None, unmatchedExport=None): 
    try:
        global workspace   
        workspace = os.path.dirname(outputShp)  # Set workspace

        # Set address, city, state, and zip variables
        address = varList[0]
        city = varList[1]
        state = varList[2]
        zip = varList[3]
        id = varList[4]

        # Read input table
        if filename.endswith('.xlsx'):  # Create dataframe if input is an Excel file
            df = pd.read_excel(filename, dtype="string", index_col=False)  
        else:  # Create dataframe if input is a CSV file
            df = pd.read_csv(filename, dtype="string", encoding="utf-8-sig", index_col=False, sep=",", engine='python')  
 
        csvTemp = None
        if geocoder == 'Geocodio (2,500 addresses per day)':  # Send addresses to Geocodio geocoder
            coordsList = geocodeWithGeocodio(df, address, city, state, zip)  
        else:  # Else send addresses to US Census geocoder
            coordsList, matchTypeList, csvTemp = geocodeWithCensus(df, address, city, state, zip, id) 
   
        if csvTemp:  # Delete csvTemp file produced by Census geocoder
            os.remove(csvTemp)

        # Create lists of x coordinates and y coordinates
        xList, yList= [], []
        for x in coordsList:
            try:
                xList.append(x[1])
                yList.append(x[0])
            except:
                xList.append(None)
                yList.append(None)

        xSeries = pd.Series(xList)  # Create a pandas series for x coordinates list
        ySeries = pd.Series(yList)  # Create a pandas series for y coordinates list
        df['X'] = xSeries  # Add X column to dataframe
        df['Y'] = ySeries  # Add Y column to dataframe

        # Add column to measure accuracy of match for Census geocoder results
        if  geocoder == 'US Census (10,000 addresses per batch file)': 
            matchSeries = pd.Series(matchTypeList)
            df['Match_Type'] = matchSeries

        geocodeDF = df[df['Y'].notnull()]  # Create dataframe with only geocoded addresses

        # Export geocoded addresses as Excel or CSV file
        if geocodedExport:
            if geocodedExport.endswith('.xlsx'):
                geocodeDF.to_excel(geocodedExport, index=False)  # Export Excel file

            else:
                geocodeDF.to_csv(geocodedExport, index=False)  # Export CSV file

        # Export unmatched addresses as Excel or CSV file
        if unmatchedExport:
            unmatchedDF = df[df['Y'].isnull()]  # Create dataframe with only unmatched addresses

            if geocoder == 'Geocodio (2,500 addresses per day)':  # Drop previously added columns if Geocodio geocoder
                unmatchedDF.drop(['X', 'Y'], axis=1, inplace=True)  
            else:  # Else Census geocoder
                unmatchedDF.drop(['X', 'Y', 'Match_Type'], axis=1, inplace=True)  # Drop extra variables

            if len(unmatchedDF) == 0:  # Print message if all addresses matched
                print('All addresses were geocoded. Unmatched addresses table not exported.')

            if unmatchedExport.endswith('.xlsx') and len(unmatchedDF) > 0:  # Export Excel file
                unmatchedDF.to_excel(unmatchedExport, index=False)

            elif unmatchedExport.endswith('.csv') and len(unmatchedDF) > 0:  # Export CSV file
                unmatchedDF.to_csv(unmatchedExport, index=False)
                
        # Create geodataframe from dataframe
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.X, df.Y), crs="EPSG:4326")
        geocodeGdf = gdf[gdf['Y'].notnull()]  # Create geodataframe with only geocoded addresses
        geocodeGdf.to_file(outputShp)  # Save shapefile

        # Create folium map
        map = folium.Map([36.5, -119.74], zoom_start=6, tiles='cartodb positron')  # Coordinates for California

        # Create list of fields and aliases for tooltip
        if not zip:
            fields = [address, city, state]
            aliases= ["Address:", "City:", "State:"]
        else:
            fields = [address, city, state, zip]
            aliases = ["Address:", "City:", "State:", "Zip:"]
    
        # Set options for tooltip
        tooltip = folium.GeoJsonTooltip(
            fields=fields,
            aliases=aliases,
            localize=True,
            sticky=False,
            labels=True,
            style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;",
            max_width=800)

        # Set options for circle marker
        circlemarker = folium.CircleMarker(
            radius=5,
            color="blue",
            weight=1,
            fill=True,
            fill_opacity=0.25,
            opacity=1)
        
        # Add features to map and zoom to features
        features = folium.features.GeoJson(geocodeGdf, name="addresses", zoom_on_click=True, tooltip=tooltip, marker=circlemarker)
        features.add_to(map)
        map.fit_bounds(map.get_bounds())
        
        # Save map as html file
        html = workspace + "/map.html"
        map.save(html)
        
        return html, len(geocodeDF), len(df)  # Return html, geocoded count, and total attempted addresses
        
    except Exception as e:
        print("An error occurred in the geocodeAddresses function.")
        print(e)
        return None
    
# Function to geocode addresses with US Census geocoder
def geocodeWithCensus(inputDf, address, city, state, zip, id): 
    try:   
        # Data must be in a specific format:
        columns = [id, address, city, state, zip]  # Data with 5 columns in order id, address, city, state, and zip
        censusDf = inputDf[columns]
        global workspace
        censusCSVTemp = workspace + r"\censusTemp.csv"
        censusDf.to_csv(censusCSVTemp, header=None, index=False)  # Data as CSV file with no header
        
        startTime = time.time()  # Set start time for geocoding profiling

        # Set options and send CSV file to Census geocoder
        url = 'https://geocoding.geo.census.gov/geocoder/geographies/addressbatch'
        payload = {'benchmark':'Public_AR_Current','vintage':'Current_Current'}
        files = {'addressFile': (censusCSVTemp, open(censusCSVTemp, 'rb'), 'text/csv')}
        s = requests.post(url, files=files, data = payload)

        # Create dataframe from reponse object s
        df = pd.read_csv(io.StringIO(s.text), sep=',', header=None, quoting=csv.QUOTE_ALL)
        df.columns = ['ID', 'ADDRESS_IN', 'MATCH_INDICATOR', 'MATCH_TYPE', 'ADDRESS_OUT', 'LONG_LAT', 'TIGER_EDGE', 'STREET_SIDE', 'FIPS_STATE', 'FIPS_COUNTY', 'CENSUS_TRACT', 'CENSUS_BLOCK']
        with pd.option_context(
            'display.width', None, 
            'display.max_columns', 7,
            'display.max_colwidth', -1,
            'display.colheader_justify', 'left'):
            print('Tail of results dataframe:\n', df.tail())

        totalTime = time.time() - startTime
        print("Geocoding", len(df), "addresses with US Census geocoder took", totalTime, "seconds")

        longlatList = list(df["LONG_LAT"])  # Create a list of the long, lat coordinates from the dataframe

        # Create a list of x, y coordinate tuples from the longlatList
        coordsList = []
        for elem in longlatList:
            try:
                split = elem.split(",")
                coordsList.append( (float(split[1]), float(split[0])) )
            except:
                coordsList.append( None )
        print('First 5 results in coordinate list:\n', coordsList[:5])  # Print first 5 coordinates
        
        return coordsList, list(df["MATCH_TYPE"]), censusCSVTemp  # Return coordinates list, match type list, and temp CSV file
    
    except Exception as e:
        print('An error occured in the geocodeWithCensus function.')
        print(e)
        return None

# Function to geocode addresses with Geocodio Python API
def geocodeWithGeocodio(inputDf, address, city, state, zip): 
    try:   
        # Create a list of full addresses
        addressList = []
        try:  # Attempt to create list of addresses
            for x in range(len(inputDf)):
                if not zip:
                    fullAddList = [ inputDf[address][x], inputDf[city][x], inputDf[state][x] ]
                else:
                    fullAddList = [ inputDf[address][x], inputDf[city][x], inputDf[state][x], inputDf[zip][x] ]
                fullString = ", ".join(fullAddList)
                addressList.append( (fullString) )

        except Exception as e:  # If an error occurs here, it is mostly likely due to missing values
            print('An error occured when creating the list of addresses. Review data for missing or null values.')
            print(e)
            addressList = None

        client = GeocodioClient('6af7cca17765cdea3dfe63cc3cd7f57ea52aa73')  # Set client variable using API key

        batches = segmentList(addressList)  # Segment address list into a batch for each core

        startTime = time.time()  # Set start time for geocoding profiling

        # Perform parallel processing 
        global cpuNum
        with multiprocessing.Pool(processes=cpuNum) as pool:  # Create the pool object 
            geocodeResults = pool.map(client.geocode, batches)  # Send batches of addresses to the geocoder

        totalTime = time.time() - startTime
        print("Geocoding", len(addressList), "addresses using", cpuNum, "processors with the Geocodio geocoder took", totalTime, "seconds") 

        # Print the number of addresses and coordinates for the first 2 batches returned from the geocoder
        for x in range(2):
            print('Batch', x+1, 'coordinate tuples with', len(geocodeResults[x].coords), 'addresses:', '\n', geocodeResults[x].coords)

        # Create a list of x, y coordinate tuples from the geocodeResults object
        coordsList = []
        for x in range(cpuNum):
            coordsList += geocodeResults[x].coords
        print('First 5 results in coordinate list:\n', coordsList[:5])  # Print first 5 coordinates
        
        return coordsList  # Return the coordinates list
    
    except Exception as e:
        print('An error occured in the geocodeWithGeocodio function.')
        print(e)
        return None

# Function to segment a list into n (cpuNum) parts
def segmentList(addList):
    try:
        array = np.array(addList)
        global cpuNum
        if len(addList) / cpuNum < 15:  # If there are less than 15 addresses in each segement 
            cpuNum = 4  # Set cpuNum to 4
        split = np.array_split(array, cpuNum)

        return [list(elem) for elem in split]  # Return a list of the segments
    
    except Exception as e:
        print('An error occurred in the segmentList function.')
        print(e)
        return None

# Function to detect 'address' in a list
def detectAdd(list):
    for field in list:
        if field.lower() == 'address':  # Set string if match
            index = list.index(field)
            string = list[index] 
            break
        elif field[:3].lower() == 'add':  # Set string if first 3 letters are 'add'
            index = list.index(field)
            string = list[index]
            break
        else:  # Else set empty string
            string = ''
    return string  # Return string

# Function to detect 'city' in a list
def detectCit(list):
    for field in list:
        if field.lower() == 'city':  # Set string if match
            index = list.index(field)
            string = list[index] 
            break
        elif field[:3].lower() == 'cit':  # Set string if first 3 letters are 'cit' 
            index = list.index(field)
            string = list[index]
            break
        else:  # Else set empty string
            string = ''
    return string  # Return string

# Function to detect 'state' in list
def detectSta(list):
    for field in list:
        if field.lower() == 'state':  # Set string if match
            index = list.index(field)
            string = list[index] 
            break
        elif field[:3].lower() == 'sta':  # Set string if first 3 letters are 'sta'
            index = list.index(field)
            string = list[index]
            break
        else:  # Else set empty string
            string = ''
    return string  # Return string

# Function to detect 'zip' in list
def detectZip(list):
    for field in list:
        if field[:3].lower() == 'zip':  # Set string if first 3 letters are 'zip'
            index = list.index(field)
            string = list[index] 
            break
        elif field[-3:].lower() == 'zip':  # Set string if last 3 letters are 'zip'
            index = list.index(field)
            string = list[index]
            break
        else:  # Else set empty string
            string = ''
    return string  # Return string

# Function to detect 'id' in string
def detectID(list):
    for field in list:
        if field[:2].lower() == 'id':  # Set string if first 2 letters are 'id'
            index = list.index(field)
            string = list[index] 
            break
        elif field[-2:].lower() == 'id':  # Set string if last 2 letters are 'id'
            index = list.index(field)
            string = list[index]
            break
        else:  # Else set empty string
            string = ''
    return string  # Return string

# Function to return a list of columns in an input table
def returnColList(filename):
    try:
        if not filename:  # If filename is an empty string return None
            return None
        
        else:
            if filename.endswith(".csv"):  # Set csvTemp variable if input table is a CSV file
                excelBool = False
                csvTemp = filename
            else:  # Set csvTemp variable if input file is an Excel file
                excelBool = True
                xlsx = pd.read_excel(filename)
                global workspace
                csvTemp = workspace + "/csv_temp.csv"
                xlsx.to_csv(csvTemp, index=False)  # Save csvTemp file to workspace

            # Create list of column names in input file
            colList = [] 
            with open(csvTemp, "r", encoding='utf-8-sig') as file:
                csv_reader = csv.reader(file)  # Set up csv reader 
                header = next(csv_reader)  # Process the header
                for col in header:  # Loop through column names in the header and add to list
                    colList.append(col)
            
            if excelBool:  # Remove csvTemp file if input file is Excel file
                os.remove(csvTemp)
                    
            return colList  # Return list of columns
    
    except Exception as e:
        print('An error occured in the returnColList function.')
        print(e)
        return None
 