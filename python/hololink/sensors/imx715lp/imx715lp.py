"""
SPDX-FileCopyrightText: Copyright (c) 2023-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import time

import hololink as hololink_module

from . import imx715lp_mode, li_i2c_expander

# Camera info
DRIVER_NAME = "IMX715"
VERSION = 1

# Camera I2C address.
CAM_I2C_ADDRESS = 0x1A


class Imx715Cam:
    def __init__(
        self,
        hololink_channel,
        i2c_bus=hololink_module.CAM_I2C_BUS,
        expander_configuration=0,
    ):
        self._hololink = hololink_channel.hololink()
        self._i2c = self._hololink.get_i2c(i2c_bus)
        self._mode = imx715lp_mode.Imx715_Mode.Unknown
        self._width = None
        self._height = None
        # Configure i2c expander on the Leopard board
        self._i2c_expander = li_i2c_expander.LII2CExpander(self._hololink, i2c_bus)
        if expander_configuration == 1:
            self._i2c_expander_configuration = (
                li_i2c_expander.I2C_Expander_Output_EN.OUTPUT_2
            )
        else:
            self._i2c_expander_configuration = (
                li_i2c_expander.I2C_Expander_Output_EN.OUTPUT_1
            )

    def setup_clock(self):
        # set the clock driver.
        # 37.125MHz
        self._hololink.setup_clock(
            hololink_module.renesas_bajoran_lite_ts3.device_configuration()
        )

    def configure(self, imx715_mode_set):
        # Make sure this is a version we know about.
        version = self.get_version()
        logging.info("version=%s" % (version,))
        assert version == VERSION

        # configure the camera based on the mode
        self.configure_camera(imx715_mode_set)

    def start(self):
        """Start Streaming"""
        self._running = True
        #
        # Setting these register is time-consuming.
        for reg, val in imx715lp_mode.imx715_start:
            if reg == imx715lp_mode.IMX715_TABLE_WAIT_MS:
                logging.debug(f"sleep {val} ms")
                time.sleep(val / 1000)  # the val is in ms
            else:
                self.set_register(reg, val)

    def stop(self):
        """Stop Streaming"""
        for reg, val in imx715lp_mode.imx715_stop:
            if reg == imx715lp_mode.IMX715_TABLE_WAIT_MS:
                logging.debug(f"sleep {val} us")
                time.sleep(val / 1000)  # the val is in ms
            else:
                self.set_register(reg, val)
        self._running = False

    def get_version(self):
        # TODO: get the version or the name of the sensor from the sensor
        return VERSION

    def get_register(self, register):
        # logging.debug("get_register(register=%d(0x%X))" % (register, register))
        self._i2c_expander.configure(self._i2c_expander_configuration.value)
        write_bytes = bytearray(100)
        serializer = hololink_module.Serializer(write_bytes)
        serializer.append_uint16_be(register)
        read_byte_count = 1
        reply = self._i2c.i2c_transaction(
            CAM_I2C_ADDRESS, write_bytes[: serializer.length()], read_byte_count
        )
        deserializer = hololink_module.Deserializer(reply)
        r = deserializer.next_uint8()
        logging.debug(
            "get_register(register=%d(0x%X)), value=%d(0x%X)"
            % (register, register, r, r)
        )
        return r

    def set_register(self, register, value, timeout=None):
        logging.debug(
            "set_register(register=%d(0x%X), value=%d(0x%X))"
            % (register, register, value, value)
        )
        self._i2c_expander.configure(self._i2c_expander_configuration.value)
        write_bytes = bytearray(100)
        serializer = hololink_module.Serializer(write_bytes)
        serializer.append_uint16_be(register)
        serializer.append_uint8(value)
        read_byte_count = 0
        self._i2c.i2c_transaction(
            CAM_I2C_ADDRESS,
            write_bytes[: serializer.length()],
            read_byte_count,
            timeout=timeout,
        )

    def configure_camera(self, imx715_mode_set):
        self.set_mode(imx715_mode_set)

        mode_list = []
        mode_4lane_common = imx715lp_mode.imx715_mode_4lane_common

        if (
            imx715_mode_set.value
            == imx715lp_mode.Imx715_Mode.IMX715_MODE_3840X2176_30FPS_10BIT.value
        ):
            mode_list = imx715lp_mode.imx715_mode_3840X2176_30fps_10bit
        elif (
            imx715_mode_set.value
            == imx715lp_mode.Imx715_Mode.IMX715_MODE_3840X2176_30FPS_12BIT.value
        ):
            mode_list = imx715lp_mode.imx715_mode_3840X2176_30fps_12bit
        elif (
            imx715_mode_set.value
            == imx715lp_mode.Imx715_Mode.IMX715_MODE_3840X2176_60FPS_10BIT.value
        ):
            mode_list = imx715lp_mode.imx715_mode_3840X2176_60fps_10bit
        elif (
            imx715_mode_set.value
            == imx715lp_mode.Imx715_Mode.IMX715_MODE_3840X2176_60FPS_12BIT.value
        ):
            mode_list = imx715lp_mode.imx715_mode_3840X2176_60fps_12bit
        elif (
            imx715_mode_set.value
            == imx715lp_mode.Imx715_Mode.IMX715_MODE_3840X2176_90FPS_10BIT.value
        ):
            mode_list = imx715lp_mode.imx715_mode_3840X2176_90fps_10bit
        else:
            logging.error(f"{imx715_mode_set} mode is not present.")

        mode_list.extend(mode_4lane_common)
        for reg, val in mode_list:
            if reg == imx715lp_mode.IMX715_TABLE_WAIT_MS:
                logging.debug(f"sleep {val} ms")
                time.sleep(val / 1000)  # the val is in ms
            else:
                self.set_register(reg, val)

    def set_exposure_reg(self, value=0x0066):
        if value < 0x00:
            value = 0x00
        vmax_lsb_value = self.get_register(imx715lp_mode.REG_VMAX_LSB)
        vmax_msb_value = self.get_register(imx715lp_mode.REG_VMAX_MSB)
        max_value = (vmax_msb_value << 8 | vmax_lsb_value) - 4
        logging.debug("The maximum of Exposure is %d(0x%X)" % (max_value, max_value))
        # The SHR between 0 and (Number of lines per frame - 4) in master mode
        shr_value = max_value - value
        if shr_value < 0x08:
            logging.warn(f"Exposure value {value} is higher than the maximum.")
            shr_value = 0x08

        self.set_register(imx715lp_mode.REG_EXP_LSB, shr_value & 0xFF)
        self.set_register(imx715lp_mode.REG_EXP_MSB, (shr_value >> 8) & 0xFF)
        time.sleep(imx715lp_mode.IMX715_WAIT_MS / 1000)

    def set_gain_reg(self, value=0x0C):
        if value < 0x00:
            logging.warn(f"Gain value {value} is lower than the minimum.")
            value = 0x00

        if value > 0xF0:
            logging.warn(f"Gain value {value} is more than maximum.")
            value = 0xF0

        self.set_register(imx715lp_mode.REG_G_LSB, value)
        time.sleep(imx715lp_mode.IMX715_WAIT_MS / 1000)

    def set_mode(self, imx715_mode_set):
        if imx715_mode_set.value < len(imx715lp_mode.Imx715_Mode):
            self._mode = imx715_mode_set
            mode = imx715lp_mode.imx_frame_format[self._mode.value]
            self._height = mode.height
            self._width = mode.width
            self._pixel_format = mode.pixel_format
        else:
            logging.error("Incorrect mode for IMX715")
            self._mode = -1

    def configure_converter(self, converter, start_byte_offset=None):
        logging.debug(
            f"configure_converter:width={self._width},height={self._height},bpp={self._pixel_format}"
        )
        start_byte = converter.receiver_start_byte()
        transmitted_line_bytes = converter.transmitted_line_bytes(
            self._pixel_format, self._width
        )
        received_line_bytes = converter.received_line_bytes(transmitted_line_bytes)
        # sensor has 1 line embeded data and 36 optical black lines before the real image data
        start_byte += 37 * received_line_bytes
        if start_byte_offset is not None:
            start_byte = start_byte_offset
        trailing_bytes = 0
        converter.configure(
            start_byte,
            received_line_bytes,
            self._width,
            self._height,
            self._pixel_format,
            trailing_bytes,
        )

    def pixel_format(self):
        return self._pixel_format

    def bayer_format(self):
        return hololink_module.sensors.csi.BayerFormat.GBRG

    def width(self):
        if self._width is None:
            raise RuntimeError(
                "Image width is unavailable; call configure_camera first."
            )
        return self._width

    def height(self):
        if self._height is None:
            raise RuntimeError(
                "Image height is unavailable; call configure_camera first."
            )
        return self._height
