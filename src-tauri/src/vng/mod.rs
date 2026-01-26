pub mod tests;
pub mod metrics;
pub mod report;

pub use tests::*;
pub use metrics::{
    detect_saccades, calculate_spv, calculate_jongkees,
    calculate_pursuit_gain, calculate_pursuit_gain_from_data,
    calculate_fixation_index, analyze_nystagmus_beats,
    get_default_reference_values, SaccadeEvent, NystagmusBeat,
    ReferenceValue as MetricReferenceValue,
};
pub use report::*;
