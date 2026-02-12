// PDCA cycle phases
export const PDCA_PHASES = ['plan', 'do', 'check', 'act'];

// Pipeline phases (9 total for 'full' preset)
export const PIPELINE_PHASES = [
  'requirements',
  'architecture',
  'design',
  'implementation',
  'unit-test',
  'integration-test',
  'code-review',
  'gap-analysis',
  'verification'
];

// Pipeline presets
export const PIPELINE_PRESETS = {
  full: {
    phases: [0, 1, 2, 3, 4, 5, 6, 7, 8],
    description: '9-stage full pipeline'
  },
  standard: {
    phases: [0, 2, 3, 4, 6, 8],
    description: '6-stage standard pipeline'
  },
  minimal: {
    phases: [2, 3, 8],
    description: '3-stage minimal pipeline'
  }
};

// State file paths (relative to .blueprint/)
export const STATE_PATHS = {
  pdca: {
    cycles: 'pdca/cycles',
    activeCycles: 'pdca/active-cycles.json',
    history: 'pdca/history'
  },
  gaps: {
    analyses: 'gaps/analyses',
    reports: 'gaps/reports'
  },
  pipeline: {
    runs: 'pipeline/runs',
    phases: 'pipeline/phases'
  }
};

// Gap severity levels
export const GAP_SEVERITY = {
  CRITICAL: { level: 4, label: 'critical' },
  HIGH: { level: 3, label: 'high' },
  MEDIUM: { level: 2, label: 'medium' },
  LOW: { level: 1, label: 'low' }
};

// PDCA cycle statuses
export const CYCLE_STATUS = {
  ACTIVE: 'active',
  SUSPENDED: 'suspended',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled'
};

// Pipeline run statuses
export const RUN_STATUS = {
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  FAILED: 'failed'
};

// Pipeline error handling modes
export const ON_ERROR = {
  ABORT: 'abort',
  SKIP: 'skip',
  PAUSE: 'pause'
};
