"""
FormulaBox Automator Configuration
Defines client-mandated default annotation settings and app configuration.
"""

import os
from pydantic import BaseModel, Field

class AnnotationConfig(BaseModel):
    """Mandatory Client Requirement Defaults:
    - Border thickness: 0.01 pt
    - Border color: Red (#E31B23 or RGB [0.89, 0.10, 0.14])
    - Fill color: None (transparent)
    """
    border_width: float = Field(default=0.01, description="Border width in points (default 0.01 pt)")
    border_color: str = Field(default="#E31B23", description="Hex color code for rectangle border")
    fill_color: str | None = Field(default=None, description="Hex color code for fill, or None for transparent")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Annotation opacity")
    only_tagged_formulas: bool = Field(default=True, description="Only box formulas inside formula tags (/Formula, /Math)")

    @property
    def rgb_stroke(self) -> tuple[float, float, float]:
        """Returns RGB tuple normalized between 0.0 and 1.0 for PyMuPDF/fitz."""
        hex_val = self.border_color.lstrip('#')
        if len(hex_val) == 6:
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            return (r, g, b)
        return (0.890, 0.106, 0.141) # Adobe Red fallback

    @property
    def rgb_fill(self) -> tuple[float, float, float] | None:
        """Returns RGB tuple for fill color, or None if transparent."""
        if not self.fill_color:
            return None
        hex_val = self.fill_color.lstrip('#')
        if len(hex_val) == 6:
            return (
                int(hex_val[0:2], 16) / 255.0,
                int(hex_val[2:4], 16) / 255.0,
                int(hex_val[4:6], 16) / 255.0
            )
        return None

DEFAULT_ANNOTATION_CONFIG = AnnotationConfig()
