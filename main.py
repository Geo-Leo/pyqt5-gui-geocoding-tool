import sys, os, multiprocessing
from core_functions import geocodeAddresses, returnColList, detectAdd, detectCit, detectSta, detectZip, detectID
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QMainWindow # QFormLayout, QWidget
from PyQt5.QtCore import QUrl
import gui_main


# Functions to handle events in GUI

def inputButtonPressed():
    fileName, _ = QFileDialog.getOpenFileName(window, "Select input Excel or CSV file", "" , "All Files (*);;Excel Files (*.xlsx);;CSV Files (*.csv)")
    if fileName:
        # Inform user if saved file extension is not correct
        if not ( fileName.endswith('.xlsx') or fileName.endswith('.csv') ):    
            QMessageBox.information(window,"Information","File must be of type with extension xlsx or csv.")
        
        else:  # Else update elements in GUI
            print("Selected input file is "+fileName)
            ui.inputLineEdit.setText(fileName)  # Set input line edit
            colValues = returnColList(fileName)  # Create a list of columns within input table
            
            # Add values to address combo box and set current text
            ui.addressComboBox.clear()
            ui.addressComboBox.addItems(colValues) 
            add = detectAdd(colValues)
            ui.addressComboBox.setCurrentText(add)

            # Add values to city combo box and set current text
            ui.cityComboBox.clear()
            ui.cityComboBox.addItems(colValues) 
            cit = detectCit(colValues)
            ui.cityComboBox.setCurrentText(cit)

            # Add values to state combo box and set current text
            ui.stateComboBox.clear()
            ui.stateComboBox.addItems(colValues) 
            sta = detectSta(colValues)
            ui.stateComboBox.setCurrentText(sta)       
            
            # Add values to zip combo box and set current text
            ui.zipComboBox.clear()
            colOptional = colValues.copy()
            colOptional.insert(0, '')
            ui.zipComboBox.addItems(colOptional)
            zip = detectZip(colValues)
            ui.zipComboBox.setCurrentText(zip)  
            
            # Add values to unique combo box and set current text
            ui.uniqueComboBox.clear()
            ui.uniqueComboBox.addItems(colValues)
            id = detectID(colValues)
            ui.uniqueComboBox.setCurrentText(id)      
    else:
        print("Open file dialog cancelled")

def geoserviceChanged():
    colValues = returnColList(ui.inputLineEdit.text())
    # If selected geocoder in combo box is Census geocoder, update elements in GUI
    if ui.geoserviceComboBox.currentText() == 'US Census (10,000 addresses per batch file)':
        ui.uniqueComboBox.setEnabled(True)
        ui.zipLabel.setText('Zip code')
        if not colValues:
            pass
        else:
            ui.zipComboBox.clear()
            ui.zipComboBox.addItems(colValues)
            zip = detectZip(colValues)
            ui.zipComboBox.setCurrentText(zip)
    else:  # Else update elements in GUI for Geocodio geocoder
        ui.uniqueComboBox.setEnabled(False)           
        ui.zipLabel.setText('Zip code (optional)')
        if not colValues:
            pass
        else:
            ui.zipComboBox.clear()
            colOptional = colValues.copy()
            colOptional.insert(0, '')
            ui.zipComboBox.addItems(colOptional) 
            zip = detectZip(colValues)
            ui.zipComboBox.setCurrentText(zip)

def saveButtonPressed(saveFileName):     
    saveFileName, _ = QFileDialog.getSaveFileName(window,"Save new shapefile as", "","Shapefile (*.shp)") 
    if saveFileName: 
        if not saveFileName.endswith('.shp'):
            # Inform user if saved file extension is not correct
            QMessageBox.information(window,"Information","Saved file must be of type with extension shp.") 
        else:  # Else set text in line edit
            print("Saved file is "+saveFileName)
            ui.outputLineEdit.setText(saveFileName) 
    else:
        print("Save file dialog cancelled")

def geocodedButtonPressed(saveFileName):     
    saveFileName, _ = QFileDialog.getSaveFileName(window,"Save export as", "","Excel Files (*.xlsx);;CSV Files (*.csv)") 
    if saveFileName:
        # Inform user if saved file extension is not correct
        if not ( saveFileName.endswith('.xlsx') or saveFileName.endswith('.csv') ):    
            QMessageBox.information(window,"Information","Saved file must be of type with extension xlsx or csv.") 
        else:  # Else set text in line edit
            print("Saved file is "+saveFileName)
            ui.geocodedLineEdit.setText(saveFileName) 
    else:
        print("Save file dialog cancelled")

def unmatchedButtonPressed(saveFileName):     
    saveFileName, _ = QFileDialog.getSaveFileName(window,"Save export as", "","Excel Files (*.xlsx);;CSV Files (*.csv)") 
    if saveFileName:  
        # Inform user if saved file extension is not correct
        if not ( saveFileName.endswith('.xlsx') or saveFileName.endswith('.csv') ):    
            QMessageBox.information(window,"Information","Saved file must be of type with extension xlsx or csv.") 
        else:  # Else set text in line edit
            print("Saved file is "+saveFileName)
            ui.unmatchedLineEdit.setText(saveFileName) 
    else:  
        print("Save file dialog cancelled")

def geocodedChecked():
    if ui.geocodedCheckBox.isChecked():  # If checked set line edit and save button to enabled
        ui.geocodedLineEdit.setEnabled(True)
        ui.geocodedSaveButton.setEnabled(True)
    else:  # Else set to disabled
        ui.geocodedLineEdit.setEnabled(False)
        ui.geocodedSaveButton.setEnabled(False)

def unmatchedChecked():
    if ui.unmatchedCheckBox.isChecked():  # If checked set line edit and save button to enabled
        ui.unmatchedLineEdit.setEnabled(True)
        ui.unmatchedSaveButton.setEnabled(True)
    else:  # Else set to disabled
        ui.unmatchedLineEdit.setEnabled(False)
        ui.unmatchedSaveButton.setEnabled(False)       

def runButtonPressed():
    # Set input variables for the geocodeAddress function
    inputTable = ui.inputLineEdit.text()
    outputShp = ui.outputLineEdit.text()
    geocoder = ui.geoserviceComboBox.currentText()

    if ui.geocodedCheckBox.isChecked():  # If checked set geocodedExport variable
        geocodedExport = ui.geocodedLineEdit.text()
    else:  # Else set to None
        geocodedExport = None

    if ui.unmatchedCheckBox.isChecked():  # If checked set unmatchedExport variable
        unmatchedExport = ui.unmatchedLineEdit.text() 
    else:  # Else set to None
        unmatchedExport = None

    # Create list of address, city, state, zip, and id variables
    address = ui.addressComboBox.currentText()
    city = ui.cityComboBox.currentText()
    state = ui.stateComboBox.currentText()
    zip = ui.zipComboBox.currentText()
    id = ui.uniqueComboBox.currentText()   
    varList = [address, city, state, zip, id]

    # Check if all file names have been specified
    filenames = [inputTable, outputShp]
    for var in filenames:
        if not var:  # Inform user if inputs are missing
            QMessageBox.information(window,"Information", "Please specify the input or output file name/s before pressing the run button.")
            break
    else:  # Run geocodeAddresses function only if input file names have been set
        try:
            # Geocode addresses and generate a html file, the count of geocoded addresses, and the count of total addresses
            html, geocodeCount, addressTotal = geocodeAddresses(inputTable, outputShp, varList, geocoder, geocodedExport, unmatchedExport)

            ui.webEngineView.load(QUrl.fromLocalFile(html))  # Load html file into webEngineView widget

            # Inform user that tool ran successfully
            msg = str(geocodeCount) + " of " + str(addressTotal) + " addresses geocoded sucessfully and saved as a shapefile!"
            QMessageBox.information(window, "Information", msg)

            os.remove(html)  # Delete html file

            print("Geocode tool ran successfully!")  # Print success message

        except Exception as e:
            print('An error occured in the runButtonPressed function.')
            print(e)

            # Inform user that tool failed
            if geocoder == 'Geocodio (2,500 addresses per day)':  # Geocodio geocoder message
                msg = "Geocoding tool failed. View terminal for error messages. Check if there are sufficient geocoding credits."
            else:  # Else Census geocoder message
                msg = "Geocoding tool failed. View terminal for error messages."
            QMessageBox.information(window,"Information", msg)
    

if __name__ == '__main__':
    # Prevent other instances of the program from opening when using multiprocessing
    multiprocessing.freeze_support()  

    try:
        app = QApplication(sys.argv)
        window = QMainWindow()  # Create empty container
        ui = gui_main.Ui_MainWindow()  # Instantiate Ui_MainWindow class
        ui.setupUi(window)  # Add the additional ui elements to main window

        # Set default file names for saved shapefile and Excel files
        cwd = os.getcwd()
        ui.outputLineEdit.setText(cwd + r'\geocoded_addresses.shp')
        ui.geocodedLineEdit.setText(cwd + r'\geocoded_addresses.xlsx')
        ui.unmatchedLineEdit.setText(cwd + r'\unmatched_addresses.xlsx')

        # Set initial state to disabled for 2 line edits, 2 save buttons, and 1 combo box
        ui.geocodedLineEdit.setEnabled(False)
        ui.geocodedSaveButton.setEnabled(False)
        ui.unmatchedLineEdit.setEnabled(False)
        ui.unmatchedSaveButton.setEnabled(False)
        ui.uniqueComboBox.setEnabled(False)
        
        # Add hard-coded values to geoserviceComboBox
        geocoderList = ['Geocodio (2,500 addresses per day)', 'US Census (10,000 addresses per batch file)']
        ui.geoserviceComboBox.addItems(geocoderList)  

        # Set connections
        ui.geoserviceComboBox.currentTextChanged.connect(geoserviceChanged)       
        ui.geocodedCheckBox.clicked.connect(geocodedChecked)    
        ui.unmatchedCheckBox.clicked.connect(unmatchedChecked)    
        ui.inputButton.clicked.connect(inputButtonPressed)    
        ui.geocodedSaveButton.clicked.connect(geocodedButtonPressed)  
        ui.unmatchedSaveButton.clicked.connect(unmatchedButtonPressed)     
        ui.outputSaveButton.clicked.connect(saveButtonPressed) 
        ui.runButton.clicked.connect(runButtonPressed)    

        window.show()

        sys.exit(app.exec_())

    except Exception as e:
        print("An error occurred in the main program.")
        print(e)  