pub mod command_popup;
pub mod footer;
pub mod header;
pub mod input;
pub mod sidebar;
pub mod transcript;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LayoutMode {
    Compact,
    Standard,
    Wide,
}

impl LayoutMode {
    pub fn from_width(w: u16) -> Self {
        if w < 80 {
            Self::Compact
        } else if w < 120 {
            Self::Standard
        } else {
            Self::Wide
        }
    }
}
