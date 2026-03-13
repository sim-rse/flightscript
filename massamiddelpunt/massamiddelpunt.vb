' ==========================================
' Export Center of Mass (Global Coordinates)
' ==========================================

Dim oAsm As AssemblyDocument
oAsm = ThisApplication.ActiveDocument

If oAsm.DocumentType <> kAssemblyDocumentObject Then
    MessageBox.Show("This rule must be run in an Assembly document.")
    Return
End If

Dim oTG As TransientGeometry
oTG = ThisApplication.TransientGeometry

' Create Excel
Dim oExcel As Object
oExcel = CreateObject("Excel.Application")
oExcel.Visible = True

Dim oWorkbook As Object
oWorkbook = oExcel.Workbooks.Add

Dim oSheet As Object
oSheet = oWorkbook.Sheets(1)

' Headers
oSheet.Cells(1,1).Value = "Component"
oSheet.Cells(1,2).Value = "Mass (kg)"
oSheet.Cells(1,3).Value = "Global X (mm)"
oSheet.Cells(1,4).Value = "Global Y (mm)"
oSheet.Cells(1,5).Value = "Global Z (mm)"

Dim row As Integer
row = 2

' Loop through all occurrences
For Each oOcc As ComponentOccurrence In oAsm.ComponentDefinition.Occurrences.AllLeafOccurrences

    Try
        Dim oDef As ComponentDefinition
        oDef = oOcc.Definition

        ' Update physical properties
        oDef.Document.Update()

        Dim massProps As MassProperties
        massProps = oDef.MassProperties

        Dim localCOM As Point
        localCOM = massProps.CenterOfMass

        ' Transform local COM to assembly space
        Dim globalCOM As Point
        globalCOM = localCOM.Copy
        globalCOM.TransformBy(oOcc.Transformation)
		
		'change the origin to be on the ground plane and not somewhere in the middle of the drone (note x and y remain the same!!)
		groundOffset = -16.8626	'distance in cm between inventor origin and desired origin (in cm)
		AdjustedZ = globalCOM.Z - groundOffset
		
        ' Convert to mm (Inventor internal units = cm)
        Dim Xmm As Double = globalCOM.X * 10
        Dim Ymm As Double = globalCOM.Y * 10
        Dim Zmm As Double = AdjustedZ * 10

        ' Write to Excel
        oSheet.Cells(row,1).Value = oOcc.Name
        oSheet.Cells(row,2).Value = massProps.Mass
        oSheet.Cells(row,3).Value = Xmm
        oSheet.Cells(row,4).Value = Ymm
        oSheet.Cells(row,5).Value = Zmm

        row = row + 1

    Catch
        ' Skip components without mass
    End Try

Next

' Autofit columns
oSheet.Columns.AutoFit()

MessageBox.Show("Export Complete!")