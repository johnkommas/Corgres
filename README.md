# Softone ERP Excel Formatter - Μορφοποιητής Excel για το Softone ERP

Μια εφαρμογή για την επεξεργασία αρχείων Excel για το σύστημα Softone ERP, αναδιατάσσοντας τις στήλες ώστε να ταιριάζουν στην απαιτούμενη μορφή.

## Περιγραφή - Description

Αυτή η εφαρμογή παρέχει μια διαδικασία ETL (Εξαγωγή, Μετασχηματισμός, Φόρτωση) για αρχεία Excel που περιέχουν πληροφορίες προϊόντων για το σύστημα Softone ERP. Επιτρέπει στους χρήστες να:

1. Ανεβάσουν αρχεία Excel με δεδομένα προϊόντων
2. Αντιστοιχίσουν τις στήλες προέλευσης στην απαιτούμενη μορφή του Softone ERP
3. Επεξεργαστούν τα δεδομένα (μετασχηματισμός και αναδιάταξη στηλών)
4. Κατεβάσουν το επεξεργασμένο αρχείο Excel

Η εφαρμογή διασφαλίζει ότι όλες οι απαιτούμενες στήλες για το σύστημα Softone ERP υπάρχουν στο αρχείο εξόδου, συμπεριλαμβανομένων των πληροφοριών προϊόντων και των δεδομένων εφοδιαστικής.

This application provides an ETL (Extract, Transform, Load) process for Excel files containing product information for the Softone ERP system. It allows users to:

1. Upload Excel files with product data
2. Map source columns to the required Softone ERP format
3. Process the data (transform and rearrange columns)
4. Download the processed Excel file

The application ensures that all required columns for the Softone ERP system are present in the output file, including product information and logistics data.

## Τεχνολογίες - Technical Stack

- **Backend**: FastAPI, Uvicorn (ανάπτυξη), Gunicorn (παραγωγή), Pandas
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Επεξεργασία Δεδομένων**: Pandas για χειρισμό Excel

- **Backend**: FastAPI, Uvicorn (development), Gunicorn (production), Pandas
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Data Processing**: Pandas for Excel manipulation

## Ξεκινώντας - Getting Started

### Προαπαιτούμενα - Prerequisites

- Python 3.7+
- pip

### Εγκατάσταση - Installation

1. Κλωνοποιήστε το αποθετήριο:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Εγκαταστήστε τις εξαρτήσεις:
   ```
   # Εγκατάσταση όλων των απαιτούμενων εξαρτήσεων
   pip install -r requirements.txt

   # Προαιρετικά: για ανάπτυξη σε περιβάλλον παραγωγής
   pip install gunicorn
   ```

3. Ρυθμίστε τις μεταβλητές περιβάλλοντος:
   Δημιουργήστε ένα αρχείο `.env` στον ριζικό κατάλογο με τις ακόλουθες μεταβλητές:
   ```
   GMAIL_USER="your-gmail-username"
   GMAIL_PASS="your-gmail-app-password"
   MAIL_FOLDER="INBOX"
   ```
   Σημείωση: Εάν χρησιμοποιείτε το Gmail με 2FA, θα χρειαστεί να δημιουργήσετε έναν Κωδικό Εφαρμογής. Μεταβείτε στον Λογαριασμό Google > Ασφάλεια > Κωδικοί Εφαρμογών.

4. Εκτελέστε την εφαρμογή:
   ```
   # Επιλογή 1: Χρησιμοποιώντας το uvicorn απευθείας
   uvicorn src.core.main:api --reload

   # Επιλογή 2: Εκτέλεση του Python script (που χρησιμοποιεί το uvicorn εσωτερικά)
   python main.py

   # Επιλογή 3: Χρησιμοποιώντας το script start_server.py (διαχειρίζεται σφάλματα "Address already in use")
   ./start_server.py
   ```

5. Ανοίξτε το πρόγραμμα περιήγησής σας και μεταβείτε στη διεύθυνση:
   ```
   http://127.0.0.1:3000/
   ```

## Πώς να το Χρησιμοποιήσετε - How to Use

1. **Ανέβασμα Αρχείου Excel**: Κάντε κλικ στο "Επιλογή Αρχείου" για να επιλέξετε ένα αρχείο Excel (.xls ή .xlsx) που περιέχει τα δεδομένα των προϊόντων σας, και στη συνέχεια κάντε κλικ στο "Ανέβασμα".

2. **Ρύθμιση Αντιστοίχισης Στηλών**: Αντιστοιχίστε τις στήλες του Excel σας στην απαιτούμενη μορφή του Softone ERP. Για κάθε απαιτούμενο πεδίο, εισάγετε το αντίστοιχο όνομα στήλης από το αρχείο Excel σας.

3. **Επεξεργασία Αρχείου**: Κάντε κλικ στο "Επεξεργασία Αρχείου" για να μετασχηματίσετε τα δεδομένα σας σύμφωνα με την αντιστοίχιση.

4. **Λήψη Αποτελέσματος**: Μόλις ολοκληρωθεί η επεξεργασία, κάντε κλικ στο "Λήψη Επεξεργασμένου Αρχείου" για να πάρετε το μετασχηματισμένο αρχείο Excel.

1. **Upload Excel File**: Click "Choose File" to select an Excel file (.xls or .xlsx) containing your product data, then click "Upload".

2. **Configure Column Mapping**: Map your source Excel columns to the required Softone ERP format. For each required field, enter the corresponding column name from your Excel file.

3. **Process File**: Click "Process File" to transform your data according to the mapping.

4. **Download Result**: Once processing is complete, click "Download Processed File" to get the transformed Excel file.

## Απαιτούμενες Στήλες - Required Columns

Η εφαρμογή απαιτεί τις ακόλουθες στήλες για το σύστημα Softone ERP:

- Barcode Προϊόντος (Product Barcode)
- Barcode Παλέτας (Pallete Barcode)
- Περιγραφή (Description)
- Κύρια Μονάδα Μέτρησης (Main Unit Measurement)
- Κατηγορία ΦΠΑ (Vat Category)
- Βάρος (Weight)
- Ύψος (Height)
- Πλάτος (Width)
- Μήκος (Length)
- Θέση Αποθήκευσης (Storage Location)
- Ελάχιστο Επίπεδο Αποθέματος (Min Stock Level)
- Μέγιστο Επίπεδο Αποθέματος (Max Stock Level)
- Σημείο Αναπαραγγελίας (Reorder Point)

The application requires the following columns for the Softone ERP system:

- Product Barcode
- Pallete Barcode
- Description
- Main Unit Measurement
- Vat Category
- Weight
- Height
- Width
- Length
- Storage Location
- Min Stock Level
- Max Stock Level
- Reorder Point

## Χαρακτηριστικά Εφαρμογής - Application Features

- Μοντέρνο, διαισθητικό περιβάλλον χρήστη με καθοδήγηση βήμα προς βήμα
- Προσαρμοστικός σχεδιασμός που λειτουργεί σε υπολογιστές και κινητές συσκευές
- Οπτική ανατροφοδότηση κατά τη διάρκεια της επεξεργασίας αρχείων
- Σαφή μηνύματα επιτυχίας/σφάλματος
- Απλοποιημένη ροή εργασίας για αποτελεσματικό μετασχηματισμό δεδομένων

- Modern, intuitive user interface with step-by-step guidance
- Responsive design that works on desktop and mobile devices
- Visual feedback during file processing
- Clear success/error messages
- Streamlined workflow for efficient data transformation

## Δομή Έργου - Project Structure

- `main.py`: Σημείο εισόδου για την εφαρμογή που εισάγει και εκτελεί το API από το src/core/main.py
- `src/`: Κύριος κατάλογος πηγαίου κώδικα
  - `core/`: Βασικές μονάδες εφαρμογής
    - `main.py`: Η κύρια εφαρμογή FastAPI που διαχειρίζεται την επεξεργασία αρχείων
    - `start_server.py`: Script για τη διαχείριση της διαδικασίας του διακομιστή
  - `data/`: Μονάδες επεξεργασίας δεδομένων
    - `etl.py`: Μονάδα ETL για μετασχηματισμό Excel
    - `column_mapper.py`: Μονάδα για την αντιστοίχιση στηλών μεταξύ μορφών προέλευσης και προορισμού
    - `uploads/`: Κατάλογος για προσωρινή αποθήκευση αρχείων Excel που ανεβαίνουν
    - `processed/`: Κατάλογος για αποθήκευση μετασχηματισμένων αρχείων Excel
  - `email/`: Μονάδες επεξεργασίας email
    - `email_scanner.py`: Μονάδα για σάρωση και επεξεργασία email με συνημμένα
  - `config/`: Αρχεία ρυθμίσεων
    - `column_mappings.json`: Αποθηκευμένες αντιστοιχίσεις στηλών για επαναχρησιμοποίηση
    - `rown_mapping.json`: Αποθηκευμένες αντιστοιχίσεις τιμών γραμμών για επαναχρησιμοποίηση
  - `static/`: Κατάλογος για στατικά αρχεία
    - `index.html`: Το όμορφα σχεδιασμένο περιβάλλον χρήστη με μοντέρνο στυλ
    - `logs.html`: Διεπαφή για προβολή αρχείων καταγραφής εφαρμογής
    - `images/`: Κατάλογος για αρχεία εικόνων
  - `tests/`: Scripts δοκιμών
    - `test_etl.py`: Script δοκιμής για τη λειτουργικότητα ETL
    - `test_column_mapper.py`: Script δοκιμής για τη λειτουργικότητα αντιστοίχισης στηλών
  - `utils/`: Βοηθητικές μονάδες
    - `logger.py`: Ρύθμιση και βοηθητικά προγράμματα καταγραφής
  - `logs/`: Κατάλογος αρχείων καταγραφής εφαρμογής

- `main.py`: Entry point for the application that imports and runs the API from src/core/main.py
- `src/`: Main source code directory
  - `core/`: Core application modules
    - `main.py`: The main FastAPI application that handles file processing
    - `start_server.py`: Script for managing the server process
  - `data/`: Data processing modules
    - `etl.py`: ETL module for Excel data transformation
    - `column_mapper.py`: Module for mapping columns between source and target formats
    - `uploads/`: Directory for temporarily storing uploaded Excel files
    - `processed/`: Directory for storing transformed Excel files
  - `email/`: Email processing modules
    - `email_scanner.py`: Module for scanning and processing emails with attachments
  - `config/`: Configuration files
    - `column_mappings.json`: Stored column mappings for reuse
    - `rown_mapping.json`: Stored row value mappings for reuse
  - `static/`: Directory for static files
    - `index.html`: The beautifully designed user interface with modern styling
    - `logs.html`: Interface for viewing application logs
    - `images/`: Directory for image files
  - `tests/`: Test scripts
    - `test_etl.py`: Test script for the ETL functionality
    - `test_column_mapper.py`: Test script for column mapping functionality
  - `utils/`: Utility modules
    - `logger.py`: Logging configuration and utilities
  - `logs/`: Application logs directory

## Δοκιμές - Testing

Για να εκτελέσετε τις δοκιμές ETL:

```
python test_etl.py
```

To run the ETL tests:

```
python test_etl.py
```

## Διαχείριση Διακομιστή - Server Management

### Χρήση του start_server.py

Το script `start_server.py` παρέχει έναν ισχυρό τρόπο εκκίνησης της εφαρμογής, αντιμετωπίζοντας κοινά προβλήματα όπως σφάλματα "Address already in use". Προσφέρει τα ακόλουθα χαρακτηριστικά:

- Αυτόματη ανίχνευση και ενεργοποίηση εικονικών περιβαλλόντων
- Έλεγχος αν η θύρα χρησιμοποιείται ήδη και τερματισμός των διαδικασιών που συγκρούονται
- Επανεκκίνηση του διακομιστή σε περίπτωση κατάρρευσης
- Παροχή σαφούς ανατροφοδότησης σχετικά με την κατάσταση του διακομιστή
- Χειρισμός ομαλού τερματισμού σε διακοπές πληκτρολογίου

Για να χρησιμοποιήσετε το script με προσαρμοσμένες ρυθμίσεις:

```
# Βασική χρήση (χρησιμοποιεί προεπιλεγμένες ρυθμίσεις: host=0.0.0.0, port=3000, με αυτόματη επαναφόρτωση)
./start_server.py

# Προσαρμοσμένος host και θύρα
./start_server.py --host 127.0.0.1 --port 8080

# Απενεργοποίηση αυτόματης επαναφόρτωσης για περιβάλλον παραγωγής
./start_server.py --no-reload
```

Το script απαιτεί το πακέτο `psutil` για τη διαχείριση διεργασιών:

```
pip install psutil
```

### Using start_server.py

The `start_server.py` script provides a robust way to start the application while handling common issues like "Address already in use" errors. It offers the following features:

- Automatically detects and activates virtual environments
- Checks if the port is already in use and stops conflicting processes
- Restarts the server if it crashes
- Provides clear feedback about server status
- Handles graceful shutdown on keyboard interrupts

To use the script with custom settings:

```
# Basic usage (uses default settings: host=0.0.0.0, port=3000, with auto-reload)
./start_server.py

# Custom host and port
./start_server.py --host 127.0.0.1 --port 8080

# Disable auto-reload for production
./start_server.py --no-reload
```

The script requires the `psutil` package for process management:

```
pip install psutil
```

## Ανάπτυξη σε Περιβάλλον Παραγωγής - Production Deployment

Για περιβάλλοντα παραγωγής, συνιστάται η χρήση του Gunicorn με εργάτες Uvicorn:

1. Εγκαταστήστε το Gunicorn:
   ```
   pip install gunicorn
   ```

2. Εκτελέστε με το Gunicorn και εργάτες Uvicorn:
   ```
   gunicorn src.core.main:api -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000
   ```

   Αυτή η ρύθμιση παρέχει καλύτερη απόδοση και αξιοπιστία για φορτία εργασίας παραγωγής.

For production environments, it's recommended to use Gunicorn with Uvicorn workers:

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```

2. Run with Gunicorn and Uvicorn workers:
   ```
   gunicorn src.core.main:api -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000
   ```

   This setup provides better performance and reliability for production workloads.

## Άδεια Χρήσης - License

Αυτό το έργο διατίθεται με άδεια MIT License - δείτε το αρχείο LICENSE για λεπτομέρειες.

This project is licensed under the MIT License - see the LICENSE file for details.
