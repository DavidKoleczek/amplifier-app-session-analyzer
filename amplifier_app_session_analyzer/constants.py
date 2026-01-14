"""Report text constants.

All user-facing strings for reports are centralized here for easy editing.
Plain text format - individual report generators handle formatting (HTML, Markdown, etc.)
"""

# Report title and metadata
REPORT_TITLE = "Amplifier Session Analysis Report"
LABEL_GENERATED = "Generated:"
LABEL_TIME_PERIOD = "Time Period:"

# Disclaimer
DISCLAIMER_TEXT = """\
Important: This report provides descriptive statistics only. \
The data being analyzed may not reflect all usage of Amplifier over the time period."""

# No data message
NO_DATA_MESSAGE = "No session data found for the specified time period."

# Average Autonomy section
HEADING_AVERAGE_AUTONOMY = "Average Autonomy Duration"
DESC_AVERAGE_AUTONOMY = """\
The average time the AI agent worked autonomously after receiving a user \
message before returning control. Measured from prompt submission to the last response: \
(prompt:submit event) to when the agent completes its response (prompt:complete event)."""

# Summary Statistics section
HEADING_SUMMARY_STATS = "Summary Statistics"
DESC_SUMMARY_STATS = """\
Key statistics about autonomous work periods."""

# Summary table labels
LABEL_METRIC = "Metric"
LABEL_VALUE = "Value"
LABEL_TOTAL_PROMPTS = "Total Prompts Sent"
LABEL_UNIQUE_SESSIONS = "Unique Sessions"
LABEL_MEAN_DURATION = "Mean Duration"
LABEL_MEDIAN_DURATION = "Median Duration"
LABEL_MAX_DURATION = "Max Duration"
LABEL_TOTAL_TIME = "Total Autonomous Time"
LABEL_STD_DEVIATION = "Std Deviation"

# Duration Distribution section
HEADING_DISTRIBUTION = "Duration Distribution"
DESC_DISTRIBUTION = """\
Breakdown of autonomy periods by duration. Shows how work is distributed \
between quick interactions and longer autonomous runs."""

# Distribution table labels
LABEL_DURATION_RANGE = "Duration Range"
LABEL_COUNT = "Count"
LABEL_PERCENTAGE = "Percentage"
LABEL_UNDER_1MIN = "Under 1 minute"
LABEL_1_5MIN = "1-5 minutes"
LABEL_5_15MIN = "5-15 minutes"
LABEL_OVER_15MIN = "Over 15 minutes"

# Session Overlap section
HEADING_OVERLAP = "Session Overlap Analysis"
DESC_OVERLAP = """\
Measures concurrent session usage. An "overlapping start" occurs when a new \
prompt is submitted in one session while another session is still processing. \
"Overlapping Session Starts" counts how many times this happened. \
"Max Parallel Sessions" is the highest number of sessions that were actively working at the same moment."""

# Overlap table labels
LABEL_OVERLAPPING_STARTS = "Overlapping Session Starts"
LABEL_MAX_PARALLEL = "Max Parallel Sessions"

# Methodology section
HEADING_METHODOLOGY = "Methodology"
METHODOLOGY_DATA_SOURCE = """\
Metrics are computed by parsing Amplifier session event logs (events.jsonl) \
from ~/.amplifier/projects/. Only user-initiated sessions are included; \
agent delegation sub-sessions are excluded from the analysis."""

# Semantic analysis configuration
SEMANTIC_BATCH_SIZE = 20  # Number of prompts to classify per LLM request
SEMANTIC_CONTEXT_WINDOW = 2  # Number of surrounding messages for context
