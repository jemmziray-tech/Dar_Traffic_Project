# Reading the dashboard

Overview compares current estimates across configured corridors. Travel-time bars show minutes for each endpoint pair; extra-delay bars show the positive difference from the provider baseline. Route lengths differ, so compare delay and the road details before drawing conclusions. The chart excludes missing and stale observations rather than replacing them with zero.

Live estimates are loaded by an explicit button. They are not stored as history, cached as a retained dataset or exported for model training. An observation older than 90 minutes is excluded from current summaries.

History accepts only independent observations with permission for retention and public display. Its line chart shows recorded travel times and a reference baseline only when one was supplied. An unknown baseline means unknown extra delay. Date windows and timestamps use Tanzania time. A small sample cannot establish a weekly pattern.

The live comparison is available before a historical dataset exists. Historical charts remain empty until eligible records are imported. CSV downloads apply only to permitted historical records. There is no prediction, city-wide efficiency score or measured productivity-loss estimate.
