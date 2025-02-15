from __future__ import annotations

import warnings
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AllowedContentSeismic(BaseModel):
    attribute: Optional[str] = Field(default=None)  # e.g. amplitude
    calculation: Optional[str] = Field(default=None)  # e.g. mean
    zrange: Optional[float] = Field(default=None)
    filter_size: Optional[float] = Field(default=None)
    scaling_factor: Optional[float] = Field(default=None)
    stacking_offset: Optional[str] = Field(default=None)

    # Deprecated
    offset: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def _check_depreciated(self) -> AllowedContentSeismic:
        if self.offset is not None:
            warnings.warn(
                "Content seismic.offset is deprecated. "
                "Please use seismic.stacking_offset insted.",
                DeprecationWarning,
            )
            self.stacking_offset, self.offset = self.offset, None
        return self


class AllowedContentProperty(BaseModel):
    attribute: str
    is_discrete: bool


class AllowedContentFluidContact(BaseModel):
    contact: str
    truncated: bool


class AllowedContentFieldOutline(BaseModel):
    contact: str


class AllowedContentFieldRegion(BaseModel):
    id: int


class AllowedContent(BaseModel):
    depth: None = Field(default=None)
    time: None = Field(default=None)
    thickness: None = Field(default=None)
    property: Optional[AllowedContentProperty] = Field(default=None)
    seismic: Optional[AllowedContentSeismic] = Field(default=None)
    fluid_contact: Optional[AllowedContentFluidContact] = Field(default=None)
    field_outline: Optional[AllowedContentFieldOutline] = Field(default=None)
    field_region: Optional[AllowedContentFieldRegion] = Field(default=None)
    regions: None = Field(default=None)
    pinchout: None = Field(default=None)
    subcrop: None = Field(default=None)
    fault_lines: None = Field(default=None)
    velocity: None = Field(default=None)
    volumes: None = Field(default=None)
    khproduct: None = Field(default=None)
    timeseries: None = Field(default=None)
    wellpicks: None = Field(default=None)
    parameters: None = Field(default=None)
    rft: None = Field(default=None)
    pvt: None = Field(default=None)
    relperm: None = Field(default=None)
    lift_curves: None = Field(default=None)
    transmissibilities: None = Field(default=None)
