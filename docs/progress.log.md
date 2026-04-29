# Limdocs Progress Log

This file lives at `docs/progress.log.md` and is used for project progress tracking. It is tracked in Git (not listed in `.gitignore`).

## How To Use

- Append new updates at the end of the current date section.
- Use one line per milestone in this format:
  - `- <what changed> | files: <paths> | status: done/in-progress`
- Keep entries short and append-only.

## 2026-03-30

- Built the initial `LoginPage` flow with separate modes for login, signup, and account confirmation in a single screen. | files: `frontend/src/pages/LoginPage.jsx` | status: done
- Connected authentication flows to AWS Cognito via Amplify Auth (`signIn`, `signUp`, `confirmSignUp`, `getCurrentUser`, `signOut`) and integrated session checks/redirect behavior. | files: `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/HomePage.jsx` | status: done
- Added Hebrew RTL authentication UI styling and reusable page feedback/error patterns for auth actions. | files: `frontend/src/pages/LoginPage.css`, `frontend/src/pages/LoginPage.jsx` | status: done
- Upgraded signup validation messages to full Hebrew requirement lists (full name, email, username, password) including multi-line password requirements rendering support. | files: `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/LoginPage.css` | status: done
- Added login Cognito error mapping by field: unknown user/email under identifier, wrong password under password, unconfirmed user message with confirm-screen link support. | files: `frontend/src/pages/LoginPage.jsx` | status: done
- Implemented clear-on-change behavior for login and signup field errors, including removal of red error border on field edit. | files: `frontend/src/pages/LoginPage.jsx` | status: done
- Reworked HomePage into a static RTL dashboard shell with right-side permanent sidebar and modern purple/indigo visual style. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/HomePage.css` | status: done
- Scoped HomePage down to basic shell only (no stats, no course grid, no search/notifications), preserving existing auth and logout behavior. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/HomePage.css` | status: done
- Fixed sidebar placement and enforced right-side behavior in RTL layout based on UI feedback iterations. | files: `frontend/src/pages/HomePage.css` | status: done
- Added local progress log setup and ignore configuration for ongoing updates. | files: `.gitignore`, `progress.log.md` | status: done
- Added global Hebrew/English language switching with persisted preference and dynamic RTL/LTR direction handling across Login and Home pages. | files: `frontend/src/main.jsx`, `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/LoginPage.css`, `frontend/src/pages/HomePage.css` | status: done
- Implemented shared language provider and translation dictionary, then renamed module naming from `i18n` to `language-control` (`LanguageControlProvider` + `languageContent`). | files: `frontend/src/language-control/LanguageControlProvider.jsx`, `frontend/src/language-control/languageContent.js`, `frontend/src/main.jsx` | status: done
- Localized Login/Home UI copy and auth feedback/errors to support both Hebrew and English while preserving existing Cognito auth logic. | files: `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/HomePage.jsx`, `frontend/src/language-control/languageContent.js` | status: done
- Updated Hebrew brand text so the Limdocs logo/name remains in English letters in login branding lines. | files: `frontend/src/language-control/languageContent.js` | status: done
- Added a styled Create Course modal popup from Home page with fields for course name, description, and visibility (private/public), including bilingual labels and placeholders. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/HomePage.css`, `frontend/src/language-control/languageContent.js` | status: done
- Split authentication into separate routes for login and register (`/login`, `/register`) while preserving existing auth flows and keeping `/` redirected to `/login`. | files: `frontend/src/App.jsx`, `frontend/src/pages/LoginPage.jsx` | status: done

## 2026-03-31

- Created DynamoDB `users` table to store Cognito user records synced after account confirmation (`user_id` as PK). | files: `AWS Console (DynamoDB)` | status: done
- Created DynamoDB `courses` table with composite key (`course_id` PK, `created_at` SK) and GSI on `owner_id` for owner-based course queries. | files: `AWS Console (DynamoDB)` | status: done
- Added Cognito Post Confirmation Lambda (Python 3.12) to sync `sub` + `email` into `users` table with ISO UTC `created_at`, wrapped in safe try/except and always returning event. | files: `AWS Console (Lambda)` | status: done
- Added Create Course Lambda (Python 3.12) behind API Gateway `POST /courses` to parse request body, extract Cognito `sub`, generate `course_id` UUID + `created_at`, and persist to `courses` table with logging/error handling and CORS response headers. | files: `AWS Console (Lambda)`, `AWS Console (API Gateway)` | status: done
- Integrated Home create-course modal submit flow with API Gateway call using Amplify session token and payload mapping (`course_name`, `description`, `is_public`) including in-flight state, inline error display, and disabled submit/cancel UI while request runs. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/HomePage.css` | status: done
- Added frontend API endpoint configuration key `VITE_API_BASE_URL` for local/prod API routing and updated env template/local env. | files: `frontend/.env.example`, `frontend/.env.local` | status: done
- Updated create-course auth header token source from Cognito Access Token to ID Token to match API Gateway REST API Cognito Authorizer expectations and resolve `401 Unauthorized` during course creation. | files: `frontend/src/pages/HomePage.jsx` | status: done
- Added a new production-ready GET User Courses Lambda (Python 3.12) for `GET /users/{userId}/courses` with safe path/authorizer user extraction, env-driven DynamoDB query config, CORS proxy response helper, and robust error handling/logging. | files: `docs/lambdas/get_user_courses_lambda.py`, `docs/lambdas/get_user_courses_lambda.md` | status: done
- Implemented frontend "Get My Courses" service layer using `axios` with Bearer ID token auth and response normalization for both object (`{courses: [...]}`) and array payload formats. | files: `frontend/src/services/coursesService.js`, `frontend/package.json` | status: done
- Wired dashboard data loading to fetch current user's courses on auth-ready mount/user change using `useEffect`, with loading state, fetch error handling, and empty-state UX. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/language-control/languageContent.js` | status: done
- Added clickable My Courses card rendering in Home page content area (course-name focused), plus new section/grid/card styles using existing project CSS system. | files: `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/HomePage.css` | status: done
- Updated dashboard greeting identity preference to show Cognito first name (`given_name`) instead of email fallback for a more user-friendly header greeting. | files: `frontend/src/pages/HomePage.jsx` | status: done
- Added post-create refresh behavior so after successful course creation the dashboard refetches courses immediately and shows the new course without manual reload. | files: `frontend/src/pages/HomePage.jsx` | status: done

## 2026-04-06

- Added backend IaC stack in-repo with SAM resources for Cognito User Pool + Client, DynamoDB `users`/`courses`, API Gateway (Cognito authorizer), and Lambda functions for create user/create course/get courses. | files: `backend/template.yaml`, `backend/src/create_user.py`, `backend/src/create_course.py`, `backend/src/get_courses.py` | status: done
- Updated user creation contract to store `username`, `first_name`, and `last_name` (instead of a single name field), with Cognito identity checks and DynamoDB persistence alignment. | files: `backend/src/create_user.py`, `frontend/src/pages/LoginPage.jsx` | status: done
- Implemented frontend user-sync flow to call `POST /users` after registration/confirmation using Cognito ID token, with pending/synced guards in storage to avoid duplicate inserts. | files: `frontend/src/pages/LoginPage.jsx` | status: done
- Added owner-scoped courses retrieval endpoint and authorization (`GET /users/{userId}/courses`) using `owner_courses_index` and strict `sub == path userId` checks. | files: `backend/src/get_courses.py`, `backend/template.yaml`, `frontend/src/services/coursesService.js`, `frontend/src/pages/HomePage.jsx` | status: done
- Standardized frontend API base URL resolution to support `VITE_API_URL` and `VITE_API_BASE_URL`, resolving stale/empty API base issues during login/home/courses flows. | files: `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/HomePage.jsx`, `frontend/src/services/coursesService.js`, `frontend/.env.example` | status: done
- Aligned create-course contract to use `course_name` and removed `title` dependency from active request/validation path. | files: `backend/src/create_course.py`, `frontend/src/pages/HomePage.jsx` | status: done
- Extended course records to include `owner_username` and `visibility` (`PUBLIC`/`PRIVATE`) based on Cognito claims and request visibility selection. | files: `backend/src/create_course.py` | status: done
- Cleaned all temporary debug instrumentation and session log artifacts after verification to return runtime code to production-clean state. | files: `frontend/src/pages/HomePage.jsx`, `.cursor/debug-216469.log` | status: done

## 2026-04-16

- Added course space route `/course/:courseId` with `CoursePage` and wired Home course cards to navigate with `courseName` in navigation state when `course_id` exists. | files: `frontend/src/App.jsx`, `frontend/src/pages/HomePage.jsx` | status: done
- Built course page shell: auth loading and guest redirect, purple banner with title from state and live materials count, upload toolbar, materials empty state (no mock cards), back-to-dashboard and language switcher with RTL/LTR layout. | files: `frontend/src/pages/CoursePage.jsx`, `frontend/src/pages/CoursePage.css` | status: done
- Added `coursePage` i18n strings (Hebrew/English) for loading, navigation, materials, upload, and empty copy; removed obsolete keys when simplifying the page. | files: `frontend/src/language-control/languageContent.js` | status: done
- Implemented upload material modal: drag-and-drop and file picker, multi-file list with remove, Cancel/Escape/backdrop, then sequential upload with session handling and modal progress/success/error copy (bilingual). | files: `frontend/src/pages/CoursePage.jsx`, `frontend/src/pages/CoursePage.css`, `frontend/src/language-control/languageContent.js` | status: done
- Added SAM/API `GenerateUploadUrlFunction` for `POST /courses/{courseId}/upload-url` with DynamoDB document row, S3 presigned `put_object`, and CORS. | files: `backend/template.yaml`, `backend/src/generate_upload_url.py` | status: done
- Added frontend documents service `getUploadUrl` + `uploadFileToS3` and wired `CoursePage` to `useParams`, `fetchAuthSession`, per-file upload, and document refetch after success. | files: `frontend/src/services/documentsService.js`, `frontend/src/pages/CoursePage.jsx` | status: done
- Added `GetCourseDocumentsFunction` for `GET /courses/{courseId}/documents` querying `CourseIdIndex` GSI and returning `{ documents }` with CORS. | files: `backend/template.yaml`, `backend/src/get_course_documents.py` | status: done
- Wired `getCourseDocuments` in the app: two-column body with Materials inner nav, load on mount when authed, document cards with filename, created time, processing badge, and count from `documents.length`. | files: `frontend/src/services/documentsService.js`, `frontend/src/pages/CoursePage.jsx` | status: done
- Extended i18n for course inner nav, documents loading/error/empty/list ARIA, and uploaded status label. | files: `frontend/src/language-control/languageContent.js` | status: done
- Documented course documents architecture and UI notes in project docs. | files: `docs/course-documents-plan.md` | status: done
- Polished course page CSS: flatter layout on page surface, sidebar separator and soft active nav, premium document cards and status pill, full-width layout with `clamp` padding (removed fixed `960px` max width on key regions). | files: `frontend/src/pages/CoursePage.css` | status: done
- Verified production build after course page and documents work. | files: `frontend/` (npm run build) | status: done

## 2026-04-29

- Added backend delete endpoint infrastructure by introducing `DeleteCourseDocumentFunction` in SAM and wiring `DELETE /courses/{courseId}/documents/{documentId}` through `LimdocsApi` with default Cognito authorizer. | files: `backend/template.yaml` | status: done
- Implemented secure delete Lambda with auth/path validation, DynamoDB lookup, owner/course authorization checks, and strict S3-first-then-Dynamo deletion order inside try/except to prevent orphaned files. | files: `backend/src/delete_document.py` | status: done
- Added future cleanup reminder in delete Lambda for Textract pipeline outputs so generated processed artifacts can be deleted when that pipeline is added. | files: `backend/src/delete_document.py` | status: done
- Added frontend documents API client method `deleteDocument(courseId, documentId, idToken)` for authenticated DELETE requests with encoded params. | files: `frontend/src/services/documentsService.js` | status: done
- Upgraded course documents UI with per-card delete action, in-progress delete state, and optimistic local removal from `documents` via `.filter()` after successful deletion. | files: `frontend/src/pages/CoursePage.jsx` | status: done
- Replaced browser `window.confirm` with a styled in-app confirmation modal matching existing CoursePage modal patterns and premium visual language. | files: `frontend/src/pages/CoursePage.jsx`, `frontend/src/pages/CoursePage.css` | status: done
- Added bilingual delete UX copy (confirm prompt/title/CTA, success, error, aria, deleting label) under `coursePage` content keys. | files: `frontend/src/language-control/languageContent.js` | status: done
- Validated new backend Lambda syntax and ran frontend lint; lint failure was due to pre-existing unrelated issues in other files, while changed delete-flow files passed without newly introduced lint problems. | files: `backend/src/delete_document.py`, `frontend/src/pages/CoursePage.jsx`, `frontend/src/services/documentsService.js`, `frontend/src/language-control/languageContent.js` | status: done
