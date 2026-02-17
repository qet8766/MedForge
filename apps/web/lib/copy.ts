export const AUTH_COPY = {
  loginTitle: "Sign in",
  loginDescription: "Sign in to your MedForge account",
  signupTitle: "Create account",
  signupDescription: "Create a new MedForge account to get started",
  submitLogin: "Sign in",
  submitSignup: "Create account",
  loginSuccess: "Signed in successfully.",
  signupSuccess: "Account created successfully.",
  logoutSuccess: "Signed out.",
  errorFallback: "Authentication failed. Please try again.",
} as const;

export const SESSION_COPY = {
  title: "Sessions",
  description: "Manage your GPU-backed development sessions",
  controlsTitle: "Session Controls",
  controlsDescription: "Manage your GPU-backed development sessions",
  createLabel: "Create Session",
  stopLabel: "Stop Current Session",
  whoamiLabel: "Check /api/v2/me",
  logoutLabel: "Sign out",
  noAction: "No session action yet.",
  noActive: "No active session.",
  notAuthenticated: "Not authenticated.",
  createFailed: "Session creation failed.",
  stopFailed: "Session stop failed.",
  stopNoSession: "No session selected to stop.",
  logoutFailed: "Sign out failed.",
  statusRunning: "Running",
  statusStarting: "Starting",
  statusStopping: "Stopping",
  statusStopped: "Stopped",
  statusError: "Error",
  openSession: "Open Session",
  sessionLabel: "Session",
  slugLabel: "Slug",
  statusLabel: "Status",
  gpuLabel: "GPU",
  createdLabel: "Created",
  startedLabel: "Started",
  stoppedLabel: "Stopped",
} as const;

export const NAV_COPY = {
  dashboard: "Dashboard",
  sessions: "Sessions",
  competitions: "Competitions",
  datasets: "Datasets",
  settings: "Settings",
  profile: "Profile",
  admin: "Admin",
  signOut: "Sign out",
} as const;

export const ERROR_COPY = {
  generic: "Something went wrong. Please try again.",
  networkError: "Network error. Check your connection and try again.",
  unauthorized: "You are not authorized to perform this action.",
  notFound: "The requested resource was not found.",
  fetchFailed: "Unable to fetch session state.",
} as const;

export const COMPETITION_COPY = {
  title: "Competitions",
  description: "Browse and participate in GPU competitions",
  leaderboard: "Leaderboard",
  submissions: "Submissions",
  submit: "Submit",
  noCompetitions: "No competitions available.",
  metricLabel: "Metric",
  scoringModeLabel: "Scoring Mode",
  submissionCapLabel: "Daily Submission Cap",
} as const;

export const DATASET_COPY = {
  title: "Datasets",
  description: "Browse available datasets",
  noDatasets: "No datasets available.",
  sourceLabel: "Source",
  licenseLabel: "License",
  sizeLabel: "Size",
  exposureLabel: "Exposure",
} as const;
