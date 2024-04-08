from datetime import timedelta
from typing import Optional

import pandas as pd

from ptp_perf.models import Sample, PTPEndpoint


class DataContainer:
    # Stages:
    # Select
    # Load
    # Process
        # Filter
    # Chart

    # Frame contents

    # Data Columns
    # | Profile Id | Endpoint Id | Endpoint Type | Vendor Id | Sample Type | Clock Stepped | Converged | Timestamp | Value

    # Processing Columns
    # | Group Id |

    # Chart columns
    # | Color |

    COLUMN_PROFILE_ID = "Profile Id"
    COLUMN_ENDPOINT_ID = "Endpoint Id"
    COLUMN_ENDPOINT_TYPE = "Endpoint Type"
    COLUMN_VENDOR_ID = "Vendor Id"
    COLUMN_SAMPLE_TYPE = "Sample Type"
    COLUMN_CLOCK_STEPPED = "Clock Stepped"
    COLUMN_CONVERGED = "Converged"
    COLUMN_TIMESTAMP = "Timestamp"
    COLUMN_VALUE = "Value"

    COLUMN_GROUP_ID = "Group Id"

    COLUMN_COLOR = "Color"

    converged_only: bool = True
    remove_clock_step: bool = True
    endpoint_normalize_time: bool = True

    data: Optional[pd.DataFrame] = None

    def load_data(self):
        data = Sample.objects.all().select_related(
            "endpoint", "endpoint__profile"
        ).values(
            "endpoint__profile__id", "endpoint__id", "endpoint__endpoint_type", "endpoint__profile__vendor_id", "sample_type", "timestamp", "value"
        )

        frame = pd.DataFrame(
            data,
        ).rename(
            columns={
                "endpoint__profile__id": self.COLUMN_PROFILE_ID,
                "endpoint__id": self.COLUMN_ENDPOINT_ID,
                "endpoint__endpoint_type": self.COLUMN_ENDPOINT_TYPE,
                "endpoint__profile__vendor_id": self.COLUMN_VENDOR_ID,
                "sample_type": self.COLUMN_SAMPLE_TYPE,
                "timestamp": self.COLUMN_TIMESTAMP,
                "value": self.COLUMN_VALUE
            }
        )

        frame[self.COLUMN_ENDPOINT_TYPE] = frame[self.COLUMN_ENDPOINT_TYPE].astype(dtype='category')
        frame[self.COLUMN_VENDOR_ID] = frame[self.COLUMN_VENDOR_ID].astype(dtype='category')
        frame[self.COLUMN_SAMPLE_TYPE] = frame[self.COLUMN_SAMPLE_TYPE].astype(dtype='category')

        self.data = frame


    def process_endpoints(self):
        for endpoint_id, endpoint_data in self.data.groupby(self.COLUMN_ENDPOINT_ID):
            endpoint = PTPEndpoint.objects.get(id=endpoint_id)
            endpoint_global_indices = self.data[self.COLUMN_ENDPOINT_ID] == endpoint_id

            # Note: All these operations apply to multiple metrics simultaneously.

            if self.converged_only:
                endpoint_data.drop(
                    endpoint_data[endpoint_data[self.COLUMN_TIMESTAMP] < endpoint.convergence_timestamp].index,
                    inplace=True
                )

            if self.remove_clock_step:
                endpoint_data.drop(
                    endpoint_data[endpoint_data[self.COLUMN_TIMESTAMP] < endpoint.clock_step_timestamp].index,
                    inplace=True
                )

            if self.endpoint_normalize_time:
                # self.data[self.COLUMN_TIMESTAMP] = self.data[self.COLUMN_TIMESTAMP].astype('int64')

                if self.converged_only:
                    self.data[endpoint_data.index, self.COLUMN_TIMESTAMP] -= endpoint.convergence_timestamp
                else:
                    self.data[endpoint_data.index, self.COLUMN_TIMESTAMP] -= endpoint.clock_step_timestamp


    def run(self):
        self.load_data()
        self.process_endpoints()
