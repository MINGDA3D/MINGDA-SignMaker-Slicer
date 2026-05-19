"""
Klipper 单喷头 G-code 导出器。

按当前 SliceResult 直接生成 G-code，并在指定高度插入用户选择的 T 宏。
"""

from __future__ import annotations

import base64
import math
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QSize, QCoreApplication

from src.app_info import APP_NAME, get_app_version

from .contour_preview import render_contour_preview_png
from .types import (
    ColorChangePoint,
    Contour,
    ExtruderType,
    GCodeParams,
    Layer,
    LayerPath,
    PathRole,
    Point,
    Point3D,
    PrinterProfile,
    SliceParams,
    SliceResult,
)

THUMBNAIL_SIZES = ((32, 32), (300, 300))
THUMBNAIL_ROW_LENGTH = 78
DEFAULT_FILAMENT_DENSITY = 1.24


class GCodeValidationError(ValueError):
    """导出前校验失败。"""
class GCodeWriter:
    """Klipper 单喷头 G-code 生成器。"""

    def __init__(self, params: Optional[GCodeParams] = None):
        self._legacy_params = params or GCodeParams()
        self.profile = self._profile_from_legacy_params(self._legacy_params)
        self._slice_params: Optional[SliceParams] = None
        self._reset_state()

    def write(
        self,
        result: SliceResult,
        output_path: str,
        slice_params: Optional[SliceParams] = None,
        printer_profile: Optional[PrinterProfile] = None,
        contours: Optional[List[Contour]] = None,
    ) -> None:
        lines = self.generate(
            result,
            slice_params=slice_params,
            printer_profile=printer_profile,
            contours=contours,
        )
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def generate(
        self,
        result: SliceResult,
        slice_params: Optional[SliceParams] = None,
        printer_profile: Optional[PrinterProfile] = None,
        contours: Optional[List[Contour]] = None,
    ) -> List[str]:
        self.profile = self._resolve_profile(slice_params, printer_profile)
        self._slice_params = slice_params
        self.validate(result, self._slice_params, self.profile)
        self._reset_state()

        lines: List[str] = []
        lines.extend(self._write_header(result, contours=contours))

        change_points = self._get_change_points(self._slice_params)
        next_change_index = 0

        for layer_index, layer in enumerate(result.layers):
            if layer_index == 1:
                lines.extend(self._write_other_layer_temperature_transition())

            while (
                next_change_index < len(change_points)
                and self._should_emit_change_before_layer(change_points[next_change_index], layer)
            ):
                change_point = change_points[next_change_index]
                lines.extend(
                    self._write_color_change(
                        change_point.macro_index,
                        change_point.height_mm,
                    )
                )
                next_change_index += 1

            lines.append("")
            lines.append(
                f"; Layer {layer_index} at Z={layer.z_height + layer.layer_height:.2f}mm"
            )
            self.current_layer_height = layer.layer_height
            lines.extend(self._write_layer(layer, is_first=(layer_index == 0)))

        lines.extend(self._write_footer(result))
        return lines

    @classmethod
    def validate(
        cls,
        result: SliceResult,
        slice_params: Optional[SliceParams],
        printer_profile: PrinterProfile,
    ) -> None:
        if result is None or not result.layers:
            raise GCodeValidationError("No processed layers available for export.")

        if printer_profile.bed_width <= 0 or printer_profile.bed_depth <= 0:
            raise GCodeValidationError("Printer printable area must be greater than zero.")
        if printer_profile.nozzle_diameter <= 0:
            raise GCodeValidationError("Nozzle diameter must be greater than zero.")
        if printer_profile.filament_diameter <= 0:
            raise GCodeValidationError("Filament diameter must be greater than zero.")
        if printer_profile.retract_length < 0:
            raise GCodeValidationError("Retract length cannot be negative.")
        if printer_profile.retract_speed <= 0:
            raise GCodeValidationError("Retract speed must be greater than zero.")
        if printer_profile.z_hop_short < 0 or printer_profile.z_hop_long < 0:
            raise GCodeValidationError("Z-hop height cannot be negative.")

        color_enabled = bool(slice_params and slice_params.color.enabled)
        change_points = cls._get_change_points(slice_params)
        if (color_enabled or change_points) and "{index}" not in printer_profile.color_change_command_template:
            raise GCodeValidationError(
                "Color change command template must contain '{index}'."
            )

        if color_enabled:
            if not change_points:
                raise GCodeValidationError(
                    QCoreApplication.translate(
                        "GCodeWriter",
                        "Color change is enabled but no change points are configured.",
                    )
                )

            previous_height = None
            shell_height = slice_params.shell.height if slice_params else 0.0
            for point in change_points:
                if point.macro_index < 0:
                    raise GCodeValidationError("Macro index must be a non-negative integer.")
                if point.height_mm <= 0 or point.height_mm >= shell_height:
                    raise GCodeValidationError(
                        "Color change heights must stay within the shell height range."
                    )
                if previous_height is not None and point.height_mm <= previous_height:
                    raise GCodeValidationError("Color change heights must be strictly increasing.")
                previous_height = point.height_mm

    @staticmethod
    def _get_change_points(slice_params: Optional[SliceParams]) -> List[ColorChangePoint]:
        if slice_params is None or not slice_params.color.enabled:
            return []
        return list(slice_params.color.change_points)

    @staticmethod
    def _profile_from_slice_params(slice_params: SliceParams) -> PrinterProfile:
        return PrinterProfile(
            id="",
            name=slice_params.machine.name or "Klipper",
            bed_width=slice_params.machine.bed_width,
            bed_depth=slice_params.machine.bed_depth,
            bed_height=slice_params.machine.bed_height,
            nozzle_diameter=slice_params.machine.nozzle_diameter,
            filament_diameter=slice_params.gcode.filament_diameter,
            retract_length=slice_params.gcode.retract_length,
            retract_speed=slice_params.gcode.retract_speed,
            z_hop_short=slice_params.gcode.z_hop_height1,
            z_hop_long=slice_params.gcode.z_hop_height2,
            long_travel_threshold=slice_params.gcode.distance_threshold,
            start_gcode=slice_params.gcode.start_gcode,
            end_gcode=slice_params.gcode.end_gcode,
            color_change_command_template=(
                slice_params.gcode.color_change_command_template or "T{index}"
            ),
        )

    @staticmethod
    def _profile_from_legacy_params(params: GCodeParams) -> PrinterProfile:
        return PrinterProfile(
            id="",
            name=params.machine_type or "Klipper",
            filament_diameter=params.filament_diameter,
            retract_length=params.retract_length,
            retract_speed=params.retract_speed,
            z_hop_short=params.z_hop_height1,
            z_hop_long=params.z_hop_height2,
            long_travel_threshold=params.distance_threshold,
            start_gcode=params.start_gcode,
            end_gcode=params.end_gcode,
            color_change_command_template=params.color_change_command_template or "T{index}",
        )

    def _resolve_profile(
        self,
        slice_params: Optional[SliceParams],
        printer_profile: Optional[PrinterProfile],
    ) -> PrinterProfile:
        if printer_profile is not None:
            return printer_profile
        if slice_params is not None:
            return self._profile_from_slice_params(slice_params)
        return self._profile_from_legacy_params(self._legacy_params)

    def _reset_state(self) -> None:
        self.current_position = Point3D(0.0, 0.0, 0.0)
        self.is_retracted = False
        self.current_layer_height = 0.3

    def _write_header(
        self,
        result: SliceResult,
        contours: Optional[List[Contour]] = None,
    ) -> List[str]:
        generated_at = datetime.now()
        app_version = get_app_version()
        first_layer_bed_temp = self._first_layer_bed_temp()
        first_layer_nozzle_temp = self._first_layer_nozzle_temp()
        lines: List[str] = self._write_summary_header_block(
            result,
            generated_at,
            app_version,
        )

        lines.append("")

        thumbnail_lines = self._write_thumbnail_blocks(contours)
        if thumbnail_lines:
            lines.extend(thumbnail_lines)
            lines.append("")

        lines.extend(self._write_orca_header_block(result, generated_at, app_version))
        lines.append("")
        lines.append("; --- Start sequence ---")

        if first_layer_bed_temp > 0:
            lines.append(f"M140 S{first_layer_bed_temp} ; Set first layer bed temperature")
        if first_layer_nozzle_temp > 0:
            lines.append(f"M104 S{first_layer_nozzle_temp} ; Set first layer nozzle temperature")
        if first_layer_bed_temp > 0:
            lines.append(f"M190 S{first_layer_bed_temp} ; Wait for first layer bed temperature")
        if first_layer_nozzle_temp > 0:
            lines.append(f"M109 S{first_layer_nozzle_temp} ; Wait for first layer nozzle temperature")

        lines.extend(self._restore_motion_state())
        if self.profile.start_gcode.strip():
            lines.append("; --- Start G-code ---")
            lines.extend(self._write_script_block(self.profile.start_gcode, result=result))
            lines.extend(self._restore_motion_state())

        lines.extend(self._write_first_layer_fan_setup())

        return lines

    def _write_summary_header_block(
        self,
        result: SliceResult,
        generated_at: datetime,
        app_version: str,
    ) -> List[str]:
        return [
            "; ========================================",
            f"; {APP_NAME} {app_version}",
            f"; Date: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"; Profile: {self.profile.name}",
            "; Firmware: Klipper",
            f"; Layers: {result.total_layers}",
            f"; Height: {result.total_height:.2f}mm",
            f"; Estimated time: {result.estimated_time / 60:.1f} min",
            f"; Estimated filament: {result.estimated_filament:.2f}m",
            "; ========================================",
        ]

    @staticmethod
    def _generated_by_line(generated_at: datetime, app_version: str) -> str:
        return (
            "; generated by OrcaSlicer "
            f"{APP_NAME} {app_version} on {generated_at.strftime('%Y-%m-%d at %H:%M:%S')}"
        )

    def _write_orca_header_block(
        self,
        result: SliceResult,
        generated_at: datetime,
        app_version: str,
    ) -> List[str]:
        return [
            "; HEADER_BLOCK_START",
            self._generated_by_line(generated_at, app_version),
            f"; total layer number: {result.total_layers}",
            f"; filament_density: {DEFAULT_FILAMENT_DENSITY:.2f}",
            f"; filament_diameter: {self.profile.filament_diameter:.2f}",
            f"; max_z_height: {result.total_height:.2f}",
            "; HEADER_BLOCK_END",
            "",
        ]

    def _write_orca_config_block(self, result: SliceResult) -> List[str]:
        config_entries = self._orca_config_entries(result)
        lines = ["; CONFIG_BLOCK_START"]
        lines.extend(
            f"; {key} = {self._format_config_value(value)}"
            for key, value in config_entries
        )
        lines.append("; CONFIG_BLOCK_END")
        return lines

    def _orca_config_entries(self, result: SliceResult) -> List[tuple[str, object]]:
        layer_height = self._config_layer_height(result)
        line_width = self._config_line_width(result, layer_height)
        wall_loops = self._config_wall_loops()
        top_layers = self._config_feature_layers(
            self._slice_params.top_face.thickness
            if self._slice_params and self._slice_params.top_face.enabled
            else 0.0,
            layer_height,
        )
        bottom_layers = self._config_feature_layers(
            self._slice_params.bottom_face.thickness
            if self._slice_params and self._slice_params.bottom_face.enabled
            else 0.0,
            layer_height,
        )
        skirt_loops = 1 if self._slice_params and self._slice_params.skirt.enabled else 0
        skirt_height = self._config_feature_layers(
            self._slice_params.skirt.height
            if self._slice_params and self._slice_params.skirt.enabled
            else 0.0,
            layer_height,
        )
        nozzle_diameter = max(self.profile.nozzle_diameter, 0.005)
        filament_diameter = max(self.profile.filament_diameter, 1.0)
        printable_area = self._config_printable_area()
        filament_used_mm = max(result.estimated_filament, 0.0) * 1000.0
        filament_weight = self._estimate_filament_weight_g(result, filament_diameter)

        return [
            ("printer_technology", "FFF"),
            ("printable_area", printable_area),
            ("bed_shape", printable_area),
            ("printable_height", self.profile.bed_height),
            ("printer_model", self.profile.name or "Klipper"),
            ("printer_notes", APP_NAME),
            ("printer_settings_id", self.profile.name or "Klipper"),
            ("print_settings_id", APP_NAME),
            ("filament_settings_id", "Generic PLA"),
            ("physical_printer_preset", self.profile.name or "Klipper"),
            ("printer_preset", self.profile.name or "Klipper"),
            ("print_preset", APP_NAME),
            ("filament_preset", "Generic PLA"),
            ("gcode_flavor", "klipper"),
            ("machine_start_gcode", self._config_script_value(self.profile.start_gcode)),
            ("machine_end_gcode", self._config_script_value(self.profile.end_gcode)),
            ("machine_pause_gcode", "PAUSE"),
            ("before_layer_change_gcode", ""),
            ("layer_change_gcode", ""),
            ("change_filament_gcode", self.profile.color_change_command_template),
            ("layer_height", layer_height),
            ("initial_layer_print_height", layer_height),
            ("first_layer_height", layer_height),
            ("line_width", line_width),
            ("initial_layer_line_width", line_width),
            ("inner_wall_line_width", line_width),
            ("outer_wall_line_width", line_width),
            ("top_surface_line_width", line_width),
            ("sparse_infill_line_width", line_width),
            ("internal_solid_infill_line_width", line_width),
            ("support_line_width", line_width),
            ("wall_loops", wall_loops),
            ("top_shell_layers", top_layers),
            ("top_shell_thickness", top_layers * layer_height),
            ("bottom_shell_layers", bottom_layers),
            ("bottom_shell_thickness", bottom_layers * layer_height),
            ("nozzle_diameter", nozzle_diameter),
            ("nozzle_type", "undefine"),
            ("nozzle_height", 4.0),
            ("default_nozzle_volume_type", "Standard"),
            ("extruder_type", "Direct Drive"),
            ("filament_diameter", filament_diameter),
            ("filament_density", DEFAULT_FILAMENT_DENSITY),
            ("filament_cost", 20.0),
            ("filament_type", "PLA"),
            ("filament_notes", ""),
            ("filament_flow_ratio", 1.0),
            ("filament_max_volumetric_speed", 0.0),
            ("filament_retraction_length", self.profile.retract_length),
            ("filament_retraction_speed", self.profile.retract_speed),
            ("filament_deretraction_speed", self.profile.retract_speed),
            ("filament_retract_before_wipe", "70%"),
            ("filament_retraction_minimum_travel", 1.0),
            ("filament_retract_when_changing_layer", 0),
            ("filament_wipe", 0),
            ("filament_wipe_distance", 2.0),
            ("filament_z_hop", self.profile.z_hop_short),
            ("nozzle_temperature_initial_layer", self._first_layer_nozzle_temp()),
            ("nozzle_temperature", self._other_layer_nozzle_temp()),
            ("nozzle_temperature_range_low", max(self._other_layer_nozzle_temp() - 20, 0)),
            ("nozzle_temperature_range_high", self._other_layer_nozzle_temp() + 20),
            ("first_layer_temperature", self._first_layer_nozzle_temp()),
            ("first_layer_bed_temperature", self._first_layer_bed_temp()),
            ("chamber_temperature", 0),
            ("overall_chamber_temperature", 0),
            ("fan_min_speed", self._first_layer_fan_percent()),
            ("fan_max_speed", self._other_layer_fan_percent()),
            ("full_fan_speed_layer", 0),
            ("close_fan_the_first_x_layers", 1),
            ("fan_cooling_layer_time", 60),
            ("slow_down_for_layer_cooling", 1),
            ("slow_down_min_speed", 10),
            ("reduce_fan_stop_start_freq", 0),
            ("dont_slow_down_outer_wall", 0),
            ("initial_layer_speed", self._first_layer_speed()),
            ("initial_layer_infill_speed", self._first_layer_speed()),
            ("outer_wall_speed", max(self._print_speed() * 0.8, 1.0)),
            ("inner_wall_speed", max(self._print_speed() * 0.8, 1.0)),
            ("small_perimeter_speed", max(self._print_speed() * 0.6, 1.0)),
            ("small_perimeter_threshold", 0),
            ("sparse_infill_speed", self._print_speed()),
            ("internal_solid_infill_speed", self._print_speed()),
            ("top_surface_speed", max(self._print_speed() * 0.6, 1.0)),
            ("bridge_speed", max(self._print_speed() * 0.5, 1.0)),
            ("gap_infill_speed", max(self._print_speed() * 0.6, 1.0)),
            ("support_speed", max(self._print_speed() * 0.8, 1.0)),
            ("support_interface_speed", max(self._print_speed() * 0.8, 1.0)),
            ("travel_speed", self._travel_speed()),
            ("travel_speed_z", 0),
            ("default_acceleration", 500),
            ("initial_layer_acceleration", 500),
            ("outer_wall_acceleration", 500),
            ("inner_wall_acceleration", 500),
            ("sparse_infill_acceleration", 500),
            ("internal_solid_infill_acceleration", 500),
            ("top_surface_acceleration", 500),
            ("bridge_acceleration", 500),
            ("travel_acceleration", 500),
            ("machine_max_acceleration_x", 500),
            ("machine_max_acceleration_y", 500),
            ("machine_max_acceleration_z", 100),
            ("machine_max_acceleration_e", 5000),
            ("machine_max_speed_x", 500),
            ("machine_max_speed_y", 500),
            ("machine_max_speed_z", 20),
            ("machine_max_speed_e", 60),
            ("machine_max_jerk_x", 10),
            ("machine_max_jerk_y", 10),
            ("machine_max_jerk_z", 0.4),
            ("machine_max_jerk_e", 5),
            ("retraction_length", self.profile.retract_length),
            ("retraction_speed", self.profile.retract_speed),
            ("deretraction_speed", self.profile.retract_speed),
            ("retraction_minimum_travel", 1.0),
            ("retract_when_changing_layer", 0),
            ("wipe", 0),
            ("wipe_distance", 2.0),
            ("retract_before_wipe", "70%"),
            ("z_hop", self.profile.z_hop_short),
            ("z_hop_types", "Normal Lift"),
            ("use_firmware_retraction", 0),
            ("extruder_clearance_radius", 70),
            ("extruder_clearance_height_to_rod", 30),
            ("extruder_clearance_height_to_lid", 90),
            ("sparse_infill_density", "15%"),
            ("sparse_infill_pattern", "rectilinear"),
            ("sparse_infill_angle", 45),
            ("top_surface_pattern", "monotonic"),
            ("bottom_surface_pattern", "monotonic"),
            ("internal_solid_infill_pattern", "rectilinear"),
            ("fill_angle", 45),
            ("infill_direction", 45),
            ("infill_wall_overlap", "15%"),
            ("detect_thin_wall", 0),
            ("xy_hole_compensation", 0),
            ("xy_contour_compensation", 0),
            ("elefant_foot_compensation", 0),
            ("elefant_foot_compensation_layers", 1),
            ("elefant_foot_layers_density", "100%"),
            ("seam_position", "aligned"),
            ("seam_slope_type", "none"),
            ("role_based_wipe_speed", 0),
            ("perimeter_generator", "classic"),
            ("wall_distribution_count", 1),
            ("wall_sequence", "inner wall/outer wall"),
            ("wall_direction", "ccw"),
            ("ensure_vertical_shell_thickness", "ensure_all"),
            ("slice_closing_radius", 0.049),
            ("slicing_mode", "regular"),
            ("bridge_flow", 1.0),
            ("internal_bridge_flow", 1.0),
            ("bridge_angle", 0),
            ("max_bridge_length", 0),
            ("brim_type", "no_brim"),
            ("brim_width", 0),
            ("brim_object_gap", 0),
            ("brim_ears", 0),
            ("skirt_type", "combined"),
            ("skirt_loops", skirt_loops),
            ("skirt_height", skirt_height),
            ("skirt_distance", 5.0),
            ("draft_shield", "disabled"),
            ("spiral_mode", 0),
            ("fuzzy_skin", "none"),
            ("fuzzy_skin_thickness", 0.1),
            ("fuzzy_skin_point_distance", 0.3),
            ("fuzzy_skin_first_layer", 0),
            ("fuzzy_skin_mode", "displacement"),
            ("fuzzy_skin_noise_type", "classic"),
            ("ironing_type", "no ironing"),
            ("ironing_flow", "10%"),
            ("ironing_spacing", 0.1),
            ("ironing_speed", 15),
            ("ironing_angle", 0),
            ("ironing_pattern", "rectilinear"),
            ("enable_support", 0),
            ("support_type", "normal(auto)"),
            ("support_style", "grid"),
            ("support_threshold_angle", 30),
            ("support_angle", 0),
            ("support_top_z_distance", 0.2),
            ("support_bottom_z_distance", 0.2),
            ("support_object_xy_distance", 0.35),
            ("support_on_build_plate_only", 0),
            ("support_base_pattern", "rectilinear"),
            ("enable_support_interface", 0),
            ("support_interface_pattern", "auto"),
            ("support_interface_spacing", 0.5),
            ("support_filament", 0),
            ("support_interface_filament", 0),
            ("flush_multiplier", 1.0),
            ("flush_into_infill", 0),
            ("flush_into_objects", 0),
            ("flush_into_support", 0),
            ("wipe_tower", 0),
            ("timelapse_type", "0"),
            ("print_sequence", "by layer"),
            ("complete_objects", 0),
            ("avoid_crossing_wall", 0),
            ("avoid_crossing_wall_max_detour", 0),
            ("arc_fitting", 0),
            ("enable_arc_fitting", 0),
            ("resolution", 0),
            ("used_filament", filament_used_mm),
            ("total_weight", filament_weight),
            ("total_cost", 0),
            ("print_time_sec", str(int(round(result.estimated_time)))),
            ("normal_print_time", self._format_duration(result.estimated_time)),
            ("silent_print_time", self._format_duration(result.estimated_time)),
        ]

    def _config_layer_height(self, result: SliceResult) -> float:
        if self._slice_params is not None and self._slice_params.shell.layer_height > 0:
            return self._slice_params.shell.layer_height
        if result.layers and result.layers[0].layer_height > 0:
            return result.layers[0].layer_height
        return 0.3

    def _config_line_width(self, result: SliceResult, layer_height: float) -> float:
        if self._slice_params is not None and self._slice_params.shell.line_width > 0:
            return self._slice_params.shell.line_width

        for layer in result.layers:
            for path in layer.paths:
                if path.line_width > 0:
                    return path.line_width

        return max(layer_height * 2.0, self.profile.nozzle_diameter)

    def _config_wall_loops(self) -> int:
        if self._slice_params is not None:
            return max(1, int(self._slice_params.shell.wall_count))
        return 2

    @staticmethod
    def _config_feature_layers(height: float, layer_height: float) -> int:
        if height <= 0 or layer_height <= 0:
            return 0
        return max(1, int(math.ceil(height / layer_height)))

    def _config_printable_area(self) -> str:
        width = max(self.profile.bed_width, 1.0)
        depth = max(self.profile.bed_depth, 1.0)
        return (
            "0x0,"
            f"{self._format_config_value(width)}x0,"
            f"{self._format_config_value(width)}x{self._format_config_value(depth)},"
            f"0x{self._format_config_value(depth)}"
        )

    @staticmethod
    def _format_config_value(value: object) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            formatted = f"{value:.4f}".rstrip("0").rstrip(".")
            return formatted or "0"
        return str(value)

    @staticmethod
    def _config_script_value(script: str) -> str:
        return (
            script.strip()
            .replace("\\", "\\\\")
            .replace("\r\n", "\\n")
            .replace("\n", "\\n")
            .replace("\r", "\\n")
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        remaining_seconds = total_seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds}s"

    @staticmethod
    def _estimate_filament_weight_g(
        result: SliceResult,
        filament_diameter: float,
    ) -> float:
        length_mm = max(result.estimated_filament, 0.0) * 1000.0
        filament_area = math.pi * (filament_diameter / 2.0) ** 2
        volume_mm3 = length_mm * filament_area
        return volume_mm3 * DEFAULT_FILAMENT_DENSITY / 1000.0

    def _write_thumbnail_blocks(self, contours: Optional[List[Contour]]) -> List[str]:
        if not contours:
            return []

        lines: List[str] = []
        emitted_sizes: set[tuple[int, int]] = set()

        for width, height in THUMBNAIL_SIZES:
            if (width, height) in emitted_sizes:
                continue
            emitted_sizes.add((width, height))

            padding = max(2, int(round(min(width, height) * 0.1)))
            stroke_width = max(1.0, min(width, height) / 90.0)
            png_data = render_contour_preview_png(
                contours,
                size=QSize(width, height),
                padding=padding,
                stroke_width=stroke_width,
            )
            if not png_data:
                continue

            encoded = base64.b64encode(png_data).decode("ascii")
            lines.extend(self._format_thumbnail_block(width, height, encoded))

        return lines

    @staticmethod
    def _format_thumbnail_block(width: int, height: int, encoded_png: str) -> List[str]:
        lines = [
            ";",
            "; THUMBNAIL_BLOCK_START",
            f"; thumbnail begin {width}x{height} {len(encoded_png)}",
        ]

        for start in range(0, len(encoded_png), THUMBNAIL_ROW_LENGTH):
            lines.append(f"; {encoded_png[start:start + THUMBNAIL_ROW_LENGTH]}")

        lines.extend(
            [
                "; thumbnail end",
                "; THUMBNAIL_BLOCK_END",
                ";",
            ]
        )
        return lines

    def _write_layer(self, layer: Layer, is_first: bool = False) -> List[str]:
        lines: List[str] = []
        z = layer.z_height + layer.layer_height
        lines.append(f"G0 Z{z:.3f} F{int(self._travel_speed() * 60)} ; Move to layer")
        self.current_position = Point3D(self.current_position.x, self.current_position.y, z)

        base_speed = self._first_layer_speed() if is_first else self._print_speed()
        for path in layer.paths:
            path_speed = self._get_path_speed(path.role, base_speed)
            lines.extend(self._write_path(path, z, path_speed))
        return lines

    def _write_path(self, path: LayerPath, z: float, speed: float) -> List[str]:
        if not path.points:
            return []

        lines = [f"; {path.role.name} path, {len(path.points)} points"]
        start = path.points[0]
        lines.extend(self._write_travel(start, z))

        if self.is_retracted:
            lines.extend(self._write_unretract())

        for point in path.points[1:]:
            lines.extend(self._write_print_move(point, z, speed, path.line_width))

        if path.is_closed and len(path.points) >= 2:
            lines.extend(self._write_print_move(start, z, speed, path.line_width))

        lines.extend(self._write_retract())
        return lines

    def _write_travel(self, target: Point, z: float) -> List[str]:
        lines: List[str] = []
        distance = self._calculate_distance_2d(
            Point(self.current_position.x, self.current_position.y),
            target,
        )
        hop_height = self._get_hop_height(distance)
        travel_z = max(self.current_position.z, z + hop_height)

        if travel_z > self.current_position.z + 1e-6:
            lines.append(f"G0 Z{travel_z:.3f} F18000 ; Z hop up")

        lines.append(
            f"G0 X{target.x:.3f} Y{target.y:.3f} F{int(self._travel_speed() * 60)} ; Travel"
        )

        if abs(travel_z - z) > 1e-6:
            lines.append(f"G0 Z{z:.3f} F18000 ; Move back to layer")

        self.current_position = Point3D(target.x, target.y, z)
        return lines

    def _write_print_move(
        self,
        target: Point,
        z: float,
        speed: float,
        line_width: float,
    ) -> List[str]:
        distance = self._calculate_distance_2d(
            Point(self.current_position.x, self.current_position.y),
            target,
        )
        extrusion = self._calculate_extrusion(distance, line_width)
        self.current_position = Point3D(target.x, target.y, z)
        return [
            f"G1 X{target.x:.3f} Y{target.y:.3f} E{extrusion:.5f} F{int(speed * 60)}"
        ]

    def _write_retract(self) -> List[str]:
        if self.is_retracted or self.profile.retract_length <= 0:
            return []
        self.is_retracted = True
        return [
            f"G1 E-{self.profile.retract_length:.5f} F{int(self.profile.retract_speed * 60)} ; Retract"
        ]

    def _write_unretract(self) -> List[str]:
        if not self.is_retracted or self.profile.retract_length <= 0:
            return []
        self.is_retracted = False
        return [
            f"G1 E{self.profile.retract_length:.5f} F{int(self.profile.retract_speed * 60)} ; Unretract"
        ]

    def _write_color_change(self, macro_index: int, height_mm: float) -> List[str]:
        lines = [
            "",
            f"; --- Color change at {height_mm:.2f}mm ---",
        ]
        lines.extend(self._write_retract())

        safe_lift = max(self.current_layer_height, self.profile.z_hop_long)
        safe_z = max(self.current_position.z, self.current_position.z + safe_lift)
        if safe_z > self.current_position.z + 1e-6:
            lines.append(f"G0 Z{safe_z:.3f} F18000 ; Raise for color change")

        command = self.profile.color_change_command_template.format(index=macro_index)
        lines.extend(self._write_script_block(command))
        lines.extend(self._restore_motion_state())

        self.current_position = Point3D(self.current_position.x, self.current_position.y, safe_z)
        self.is_retracted = False
        return lines

    def _write_other_layer_temperature_transition(self) -> List[str]:
        first_layer_nozzle_temp = self._first_layer_nozzle_temp()
        other_layer_nozzle_temp = self._other_layer_nozzle_temp()
        first_layer_bed_temp = self._first_layer_bed_temp()
        other_layer_bed_temp = self._other_layer_bed_temp()
        first_layer_fan_percent = self._first_layer_fan_percent()
        other_layer_fan_percent = self._other_layer_fan_percent()

        if (
            first_layer_nozzle_temp == other_layer_nozzle_temp
            and first_layer_bed_temp == other_layer_bed_temp
            and first_layer_fan_percent == other_layer_fan_percent
        ):
            return []

        lines = [
            "",
            "; --- Print settings transition after first layer ---",
        ]

        if first_layer_bed_temp != other_layer_bed_temp:
            lines.append(f"M140 S{other_layer_bed_temp} ; Set other layers bed temperature")
        if first_layer_nozzle_temp != other_layer_nozzle_temp:
            lines.append(f"M104 S{other_layer_nozzle_temp} ; Set other layers nozzle temperature")

        if first_layer_bed_temp != other_layer_bed_temp and other_layer_bed_temp > 0:
            lines.append(f"M190 S{other_layer_bed_temp} ; Wait for other layers bed temperature")
        if first_layer_nozzle_temp != other_layer_nozzle_temp:
            if other_layer_nozzle_temp > 0:
                lines.append(f"M109 S{other_layer_nozzle_temp} ; Wait for other layers nozzle temperature")

        if first_layer_fan_percent != other_layer_fan_percent:
            lines.extend(self._write_fan_command(other_layer_fan_percent, "other layers"))

        return lines

    def _write_footer(self, result: SliceResult) -> List[str]:
        lines = [
            "",
            "; --- End sequence ---",
        ]

        end_z = min(
            self.profile.bed_height,
            max(self.current_position.z, 0.0) + max(self.current_layer_height, 5.0),
        )
        if end_z > self.current_position.z + 1e-6:
            lines.append(f"G0 Z{end_z:.3f} F18000 ; Raise Z")

        lines.append("G92 E0 ; Reset extruder")
        if self.profile.end_gcode.strip():
            lines.append("; --- End G-code ---")
            lines.extend(self._write_script_block(self.profile.end_gcode))

        lines.extend(
            [
                "M104 S0 ; Turn off nozzle",
                "M140 S0 ; Turn off bed",
                "M84 ; Disable motors",
                "",
                "; --- Print statistics ---",
                f"; total filament used [mm] = {self._format_config_value(result.estimated_filament * 1000.0)}",
                f"; total layers count = {result.total_layers}",
                f"; estimated printing time (normal mode) = {self._format_duration(result.estimated_time)}",
                "",
            ]
        )
        lines.extend(self._write_orca_config_block(result))
        lines.extend(["", "; === End of file ==="])
        return lines

    def _write_script_block(
        self,
        script: str,
        *,
        result: Optional[SliceResult] = None,
    ) -> List[str]:
        rendered_script = self._render_script_template(script, result=result)
        return [line.rstrip() for line in rendered_script.splitlines() if line.strip()]

    def _render_script_template(
        self,
        script: str,
        *,
        result: Optional[SliceResult] = None,
    ) -> str:
        replacements = {
            "{nozzle_temperature_initial_layer[0]}": str(self._first_layer_nozzle_temp()),
            "[first_layer_bed_temperature]": str(self._first_layer_bed_temp()),
            "{first_layer_bed_temperature}": str(self._first_layer_bed_temp()),
            "[initial_tool]": str(self._initial_tool(result)),
            "{initial_tool}": str(self._initial_tool(result)),
        }

        rendered_script = script
        for token, value in replacements.items():
            rendered_script = rendered_script.replace(token, value)
        return rendered_script

    def _initial_tool(self, result: Optional[SliceResult]) -> int:
        if result is None or not result.layers:
            return 0

        first_layer = result.layers[0]
        if isinstance(first_layer.extruder, ExtruderType):
            return max(first_layer.extruder.value - 1, 0)

        for path in first_layer.paths:
            if isinstance(path.extruder, ExtruderType):
                return max(path.extruder.value - 1, 0)

        return 0

    def _restore_motion_state(self) -> List[str]:
        return [
            "G90 ; Absolute positioning",
            "M83 ; Relative extrusion",
            "G92 E0 ; Reset extruder",
        ]

    def _print_speed(self) -> float:
        if self._slice_params is not None:
            return self._slice_params.speed.print_speed
        return self._legacy_params.print_speed

    def _travel_speed(self) -> float:
        if self._slice_params is not None:
            return self._slice_params.speed.travel_speed
        return self._legacy_params.travel_speed

    def _first_layer_speed(self) -> float:
        if self._slice_params is not None:
            return self._slice_params.speed.first_layer_speed
        return self._legacy_params.first_layer_speed

    def _first_layer_nozzle_temp(self) -> int:
        if self._slice_params is not None:
            return self._slice_params.gcode.first_layer_nozzle_temp
        return self._legacy_params.first_layer_nozzle_temp

    def _other_layer_nozzle_temp(self) -> int:
        if self._slice_params is not None:
            return self._slice_params.gcode.other_layer_nozzle_temp
        return self._legacy_params.other_layer_nozzle_temp

    def _first_layer_bed_temp(self) -> int:
        if self._slice_params is not None:
            return self._slice_params.gcode.first_layer_bed_temp
        return self._legacy_params.first_layer_bed_temp

    def _other_layer_bed_temp(self) -> int:
        if self._slice_params is not None:
            return self._slice_params.gcode.other_layer_bed_temp
        return self._legacy_params.other_layer_bed_temp

    def _first_layer_fan_percent(self) -> int:
        if self._slice_params is not None:
            return self._clamp_fan_percent(self._slice_params.gcode.first_layer_fan_percent)
        return self._clamp_fan_percent(self._legacy_params.first_layer_fan_percent)

    def _other_layer_fan_percent(self) -> int:
        if self._slice_params is not None:
            return self._clamp_fan_percent(self._slice_params.gcode.other_layer_fan_percent)
        return self._clamp_fan_percent(self._legacy_params.other_layer_fan_percent)

    def _write_first_layer_fan_setup(self) -> List[str]:
        return self._write_fan_command(self._first_layer_fan_percent(), "first layer")

    @staticmethod
    def _clamp_fan_percent(value: int) -> int:
        return max(0, min(int(value), 100))

    @classmethod
    def _fan_pwm_from_percent(cls, percent: int) -> int:
        clamped_percent = cls._clamp_fan_percent(percent)
        return int(round((clamped_percent / 100.0) * 255))

    def _write_fan_command(self, percent: int, target: str) -> List[str]:
        clamped_percent = self._clamp_fan_percent(percent)
        if clamped_percent <= 0:
            return [f"M107 ; Turn off fan for {target}"]
        return [
            f"M106 S{self._fan_pwm_from_percent(clamped_percent)} ; "
            f"Set {target} fan speed to {clamped_percent}%"
        ]

    def _get_path_speed(self, role: PathRole, base_speed: float) -> float:
        if (
            role == PathRole.SKIRT
            and self._slice_params is not None
            and self._slice_params.skirt.speed > 0
        ):
            return self._slice_params.skirt.speed
        if (
            role in {PathRole.STEP, PathRole.V_GROOVE}
            and self._slice_params is not None
            and self._slice_params.step.print_speed > 0
        ):
            return self._slice_params.step.print_speed

        speed_multipliers = {
            PathRole.WALL: 0.8,
            PathRole.PRIME_TOWER: 0.8,
            PathRole.SAFETY_LINE: 1.0,
            PathRole.SKIRT: 1.0,
            PathRole.STEP: 0.7,
            PathRole.V_GROOVE: 0.7,
            PathRole.FILL_PANEL: 1.2,
            PathRole.FILL_GRID: 1.2,
            PathRole.FILL_BASEPLATE: 1.0,
            PathRole.FILL_BOTTOM_FACE: 0.8,
            PathRole.LIGHT_SLOT: 0.8,
            PathRole.FILL_TOP_FACE: 0.8,
            PathRole.EDGE_WRAP: 0.6,
            PathRole.OUTLINE: 0.5,
            PathRole.CONNECTED: 0.8,
        }
        return base_speed * speed_multipliers.get(role, 1.0)

    @staticmethod
    def _should_emit_change_before_layer(change_point: ColorChangePoint, layer: Layer) -> bool:
        return layer.z_height + 1e-6 >= change_point.height_mm

    @staticmethod
    def _calculate_distance_2d(p1: Point, p2: Point) -> float:
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    def _calculate_extrusion(self, distance: float, line_width: float) -> float:
        filament_area = math.pi * (self.profile.filament_diameter / 2) ** 2
        extrusion_area = line_width * self.current_layer_height
        return distance * extrusion_area / filament_area

    def _get_hop_height(self, distance: float) -> float:
        if distance > self.profile.long_travel_threshold:
            return self.profile.z_hop_long
        if distance > 10:
            return self.profile.z_hop_short
        return 0.0


def write_gcode(
    result: SliceResult,
    output_path: str,
    params: Optional[SliceParams] = None,
    printer_profile: Optional[PrinterProfile] = None,
    contours: Optional[List[Contour]] = None,
) -> None:
    """便捷函数：生成并写入 G-code 文件。"""
    legacy_params = params.gcode if params else GCodeParams()
    writer = GCodeWriter(legacy_params)
    writer.write(
        result,
        output_path,
        slice_params=params,
        printer_profile=printer_profile,
        contours=contours,
    )
