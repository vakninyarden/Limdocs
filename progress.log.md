# Progress log

## Course Space (course page) — web app

### Routing and navigation

- Added route `/course/:courseId` in `web/src/App.jsx` with `CoursePage` component.
- `web/src/pages/HomePage.jsx`: course cards navigate to `/course/:courseId` with `state: { courseName }` when a course id exists; no navigation if id is missing.

### Course page UI (`web/src/pages/CoursePage.jsx` + `CoursePage.css`)

- Auth: loading state, then redirect guests to `/` (same idea as Home) when not signed in.
- Purple banner: course title from navigation state, fallback to untitled course string; materials count (later wired to live document list — see below).
- Toolbar: **Upload material** button (label from i18n), aligned to logical start for RTL/LTR.
- Materials section: heading + empty state (no mock document cards).
- **No** Questions tab, **no** course id in the banner, **no** sample/example files.
- Top bar: **Back to dashboard** → `navigate('/home')`, plus existing language switcher; layout respects RTL/LTR.

### Internationalization

- `web/src/language-control/languageContent.js`: `coursePage` keys in Hebrew and English (loading, back to dashboard, materials stat template, upload, materials section labels, empty materials copy). Removed obsolete keys when tabs/mock content were dropped.

### Build

- `npm run build` in `web/` succeeds after these changes.

---

## Upload modal (UI only, then wired to API)

- **`web/src/pages/CoursePage.jsx`**: Modal opens from **Upload material**; drag-and-drop or file picker; multi-file list with remove; Cancel / Escape / backdrop; Upload triggers flow (initially placeholder, then real upload).
- **`web/src/pages/CoursePage.css`**: Modal backdrop, dropzone, file list, actions (aligned with HomePage modal patterns).
- **`web/src/language-control/languageContent.js`**: Strings for upload modal (en/he): title, subtitle, drop hint, selected files, submit, progress, success/error, session/API messages.

---

## S3 pre-signed URL upload (backend + frontend)

### Backend (`backend/`)

- **`template.yaml`**: `GenerateUploadUrlFunction` — `POST /courses/{courseId}/upload-url`, LabRole, env `DOCUMENTS_TABLE`, `UPLOAD_BUCKET` (RawUploadsBucket).
- **`src/generate_upload_url.py`**: Cognito `sub` from authorizer; path `courseId`; body `file_name`, `file_type`; `document_id` + DynamoDB item (`processing_status` UPLOADED, etc.); S3 key `uploads/{courseId}/{document_id}_{safe_name}`; `boto3` presigned `put_object` with `ContentType`; JSON `upload_url`, `document_id`, `s3_key` + CORS headers.

### Frontend (`web/`)

- **`src/services/documentsService.js`**: `getUploadUrl`, `uploadFileToS3` (axios PUT with `Content-Type` matching presign).
- **`CoursePage.jsx`**: `useParams` for `courseId`; `fetchAuthSession` + sequential upload per file; loading/progress/error/success in modal; refetch documents after successful upload (see below).

---

## Course documents list + inner layout

### Backend

- **`template.yaml`**: `GetCourseDocumentsFunction` — `GET /courses/{courseId}/documents`, env `DOCUMENTS_TABLE`, `INDEX_NAME: CourseIdIndex`.
- **`src/get_course_documents.py`**: Auth via claims; query GSI `CourseIdIndex` with `Key("course_id").eq(course_id)`; returns `{ "documents": items }` + CORS.

### Frontend

- **`documentsService.js`**: `getCourseDocuments(courseId, idToken)`.
- **`CoursePage.jsx`**: Two-column **`course-page__body`** — inner sidebar tab **Materials** (`activeTab`), main area with materials header (title + Upload), `loadDocuments` on mount when authed; document cards (`original_file_name`, `created_at`, `processing_status` badge); materials count from **`documents.length`** (no mock).
- **`languageContent.js`**: `tabMaterials`, `courseInnerNavAria`, `documentsLoading`, `documentsError`, `documentsListEmpty`, `documentsListAriaLabel`, `statusUploaded` (en/he).

### Docs

- **`docs/course-documents-plan.md`**: Plain-markdown plan (architecture + UI notes).

---

## Course page layout polish

- **Premium minimalist CSS** (`CoursePage.css`): Removed “boxed” outer card from `course-page__body` (layout on `--surface-page`); inner sidebar as column with hairline separator only; nav active state soft tint + blue text (not solid primary); document cards white background, generous padding, shadow + hairline; status badge soft pill (`#e8f4ff` / `#007aff`); materials header spacing and alignment.
- **Full-width layout**: Removed `960px` max-width from top bar, banner, and body; `course-page` uses `width: 100%` and `clamp` horizontal padding so content uses the full viewport width.

### Build

- `npm run build` in `web/` succeeds after the above.

---

*Last updated: upload presign + documents GET API, documents list UI with inner nav, full-width course page, progress log sync.*
