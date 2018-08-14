/*
 * Copyright 2018 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef THIRD_PARTY_STRATUM_HAL_LIB_PHAL_ONLP_SFP_DATASOURCE_H_
#define THIRD_PARTY_STRATUM_HAL_LIB_PHAL_ONLP_SFP_DATASOURCE_H_

#include "stratum/hal/lib/common/common.pb.h"
#include "stratum/hal/lib/phal/datasource.h"
#include "stratum/hal/lib/phal/onlp/onlp_wrapper.h"
#include "stratum/hal/lib/phal/phal.pb.h"
#include "stratum/hal/lib/phal/system_interface.h"
#include "stratum/lib/macros.h"
#include "absl/base/integral_types.h"
#include "absl/memory/memory.h"
#include "util/task/status.h"
#include "util/task/statusor.h"

namespace stratum {
namespace hal {
namespace phal {
namespace onlp {

class OnlpSfpDataSource : public DataSource {
  // Makes a shared_ptr to an SfpDataSource which manages an ONLP SFP object.
  // Returns error if the OID object is not of the correct type or not present.
 public:
  // OnlpSfpDataSource does not take ownership of onlp_interface. We expect
  // onlp_interface remains valid during OnlpSfpDataSource's lifetime.
  static ::util::StatusOr<std::shared_ptr<OnlpSfpDataSource>> Make(
      OnlpOid sfp_id, OnlpInterface* onlp_interface, CachePolicy* cache_policy);

  // Accessors for managed attributes.
  ManagedAttribute* GetSfpId() { return &sfp_id_; }
  ManagedAttribute* GetSfpHardwareState() { return &sfp_hw_state_; }
  ManagedAttribute* GetSfpMediaType() { return &media_type_; }
  ManagedAttribute* GetSfpVendor() { return &sfp_vendor_; }
  ManagedAttribute* GetSfpModel() { return &sfp_model_name_; }
  ManagedAttribute* GetSfpSerialNumber() { return &sfp_serial_number_; }
  ManagedAttribute* GetSfpTemperature() { return &temperature_; }
  ManagedAttribute* GetSfpVoltage() { return &vcc_; }
  ManagedAttribute* GetSfpRxPower(int channel_index) {
    return &rx_power_[channel_index];
  }
  ManagedAttribute* GetSfpTxPower(int channel_index) {
    return &tx_power_[channel_index];
  }
  ManagedAttribute* GetSfpTxBias(int channel_index) {
    return &tx_bias_[channel_index];
  }

 private:
  OnlpSfpDataSource(OnlpOid sfp_id, OnlpInterface* onlp_interface,
                    CachePolicy* cache_policy, const SfpInfo& sfp_info);

  static ::util::Status ValidateOnlpSfpInfo(OnlpOid oid,
                                            OnlpInterface* onlp_interface) {
    ASSIGN_OR_RETURN(SfpInfo sfp_info, onlp_interface->GetSfpInfo(oid));
    CHECK_RETURN_IF_FALSE(sfp_info.Present())
        << "The SFP with OID " << oid << " is not currently present.";
    return ::util::OkStatus();
  }

  ::util::Status UpdateValues() override;

  OnlpOid sfp_oid_;

  // We do not own ONLP stub object. ONLP stub is created on PHAL creation and
  // destroyed when PHAL deconstruct. Do not delete onlp_stub_.
  OnlpInterface* onlp_stub_;

  // A list of managed attributes.
  // Hardware Info.
  TypedAttribute<OnlpOid> sfp_id_{this};
  EnumAttribute sfp_hw_state_{HwState_descriptor(), this};
  TypedAttribute<std::string> sfp_vendor_{this};
  TypedAttribute<std::string> sfp_model_name_{this};
  TypedAttribute<std::string> sfp_serial_number_{this};

  // Media Type.
  EnumAttribute media_type_{MediaType_descriptor(), this};

  // SFP temperature.
  TypedAttribute<double> temperature_{this};
  TypedAttribute<double> vcc_{this};

  // Channels info.
  std::vector<TypedAttribute<double>> rx_power_;
  std::vector<TypedAttribute<double>> tx_power_;
  std::vector<TypedAttribute<double>> tx_bias_;
};

}  // namespace onlp
}  // namespace phal
}  // namespace hal
}  // namespace stratum

#endif  // THIRD_PARTY_STRATUM_HAL_LIB_PHAL_ONLP_SFP_DATASOURCE_H_
