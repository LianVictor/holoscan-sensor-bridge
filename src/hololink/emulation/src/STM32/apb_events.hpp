/**
 * SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * See README.md for detailed information.
 */

#ifndef STM32_APB_EVENTS_H
#define STM32_APB_EVENTS_H

#include "hsb_config.hpp"

namespace hololink::emulation {

int async_event_readback_cb(void* ctxt, struct AddressValuePair* addr_val, int max_count);
int async_event_configure_cb(void* ctxt, struct AddressValuePair* addr_val, int max_count);

int apb_ram_read(void* ctxt, struct AddressValuePair* addr_val, int max_count);
int apb_ram_write(void* ctxt, struct AddressValuePair* addr_val, int max_count);

int handle_apb_sw_event(void* ctxt, struct AddressValuePair* addr_val, int max_count);

}

#endif