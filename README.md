# VVITU LibSphere

A runnable Flask digital library management prototype with physical-copy accession tracking, barcode lookup, circulation, reservations, digital resource uploads, lifetime copy history, dashboards and dark/light UI.

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   python app.py
   ```
5. Open http://127.0.0.1:5000

## Demo accounts

- Admin: `admin` / `Admin@123`
- Librarian: `librarian` / `Lib@123`
- Student: `student` / `Student@123`

Change all demo passwords and `SECRET_KEY` before any real deployment.

## Included functionality

- Search by title, author, ISBN, call number, ACC.NO and barcode.
- Each physical copy has its own unique ACC.NO; barcode value equals ACC.NO.
- Duplicate ACC.NO prevention.
- Book passport with acquisition details, circulation history and event log.
- Librarian registration, issue and return workflows.
- Student reservations with FIFO queue and notification on return.
- PDF/EPUB digital resource uploads.
- In-browser barcode camera scanner (camera requires localhost or HTTPS).
- Responsive dark/light interface, CSS 3D book cards and animated landing page.

## Notes / prototype limitations

This is a complete local academic prototype, not an officially integrated VVITU system. It uses a local SQLite database (`libsphere.db`) and local file uploads. No existing university records are imported. Sample seed records and demo credentials are created on first run. The 3D visuals are lightweight CSS-based effects; external CDN libraries are used for ZXing and Chart.js availability, and the current build does not require a 3D graphics engine for core workflows. Fine payments, automated email delivery, reservation expiry jobs, advanced reporting, account self-registration, CSRF hardening and production deployment configuration are future enhancements. Back up the database and uploaded files.

## Accounts and institutional email rules

- Student self-registration accepts only email addresses ending exactly in `@vvitu.ac.in` or `@vvit.net`.
- Login is by institutional email address, not username.
- New self-registered accounts receive the `student` role. An administrator creates faculty/librarian accounts or changes user roles.
- Admin → **Manage Users** supports creating accounts, searching users, changing roles, and activating/deactivating accounts.
- **Profile** lets each signed-in user update their display name and upload a PNG, JPG, JPEG or WEBP profile picture.
- The domain check restricts the email suffix; it does not prove mailbox ownership. Email OTP/verification requires an institutional SMTP account and is not enabled in this build.

## Database configuration

- Default local database: SQLite at `libsphere.db`.
- For a shared deployment, configure `DATABASE_URL` to a PostgreSQL connection string, for example `postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE`.
- Set a strong random `SECRET_KEY` in the environment before deployment.
- The app includes a small additive startup migration for the new profile and active-account columns. Back up an existing database before upgrading.
- Database records and uploaded profile images are separate. Back up the database and `static/uploads/` together.

## Barcode scanner

There are two separate barcode workflows:
1. **Barcode Scanner**: staff scan or manually enter ACC.NO/barcode to retrieve the existing physical copy's book passport and current status.
2. **Register a physical copy**: use **Scan existing barcode** beside the ACC.NO field to scan the book while adding it. The scanned value fills ACC.NO; it is saved as the copy's barcode value.

The scanner tries common 1D formats (Code 128, Code 39, EAN-13/8, ITF, Codabar and UPC-A/E). Camera access requires localhost or HTTPS, browser camera permission, and network access to load ZXing from its CDN. Some older or non-standard printed barcodes may not decode; use the printed accession number manually as a fallback.
