# v0.5.0 — Multi-area filtering and safer follow-up alerts

- Select multiple JMA EEW prefecture forecast areas (OR matching)
- Enter fine subdivisions such as `神奈川県東部` as custom values
- Accept familiar aliases such as `神奈川県`, `東京都`, `北海道`, and `沖縄県`
- Set a minimum predicted seismic intensity from 4 through 7
- Keep evaluating follow-up reports until both area and intensity conditions match
- Emit `p2p_eew_update` when a later report raises the predicted maximum intensity
- Process cancellations only for events that previously triggered an alert
- Stop Blueprint audio on cancellation when enabled
- Change settings later from the integration options UI with automatic reload
- Automatically migrate v0.4 and earlier single-area configuration
- Add unit tests for area normalization, multiple-area matching, and intensity parsing
- Expand the public README with installation, configuration, event reference, examples, troubleshooting, privacy, and safety guidance
