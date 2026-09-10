"""
Official MoSPI eSankhyiki CPI Benchmark Ingestion Client for RAPA.
Uses the official `mospi-esankhyiki` Python package.
Handles:
1. Discovery of available datasets, indicators, and metadata.
2. Ingestion of official CPI Item 294 ("Airfare", code 07.3.3.1.2.01) from Base 2024.
3. Ingestion of official CPI Transport & Communication series from Base 2012.
4. Truthful logging of all attempts, successes, and explicit API exceptions into SQLite.
"""

from typing import Dict, Any, List, Optional
import esankhyiki
from data.db import (
    insert_cpi_records, 
    log_ingestion, 
    DB_PATH, 
    init_db,
    LATEST_BENCHMARK_YEAR,
    LATEST_BENCHMARK_MONTH,
    LATEST_BENCHMARK_PERIOD,
    OFFICIAL_MOSPI_JULY_2026
)


class MoSPIBenchmarkClient:
    """Client for official MoSPI eSankhyiki CPI API with full audit logging."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def discover_cpi_metadata(self, base_year: str = "2024", level: str = "Item") -> Dict[str, Any]:
        """
        Calls get_metadata on MoSPI eSankhyiki for CPI and extracts structural items/groups.
        """
        try:
            meta = esankhyiki.get_metadata("CPI", base_year=base_year, level=level, series="Current")
            raw_items = meta[0].get("item", []) if isinstance(meta, list) and meta else []

            # Extract air travel / transport items
            transport_items = [
                i for i in raw_items
                if any(k in str(i.get("item_name", "")).lower() for k in ["air", "flight", "transport", "fare", "rail", "bus", "taxi"])
            ]

            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation="discover_cpi_metadata",
                status="SUCCESS",
                records_ingested=len(transport_items),
                details={"total_items": len(raw_items), "transport_items_count": len(transport_items)},
                db_path=self.db_path
            )

            return {
                "status": "success",
                "base_year": base_year,
                "level": level,
                "total_items_count": len(raw_items),
                "transport_items": transport_items,
                "full_metadata": meta
            }
        except Exception as e:
            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation="discover_cpi_metadata",
                status="FAILURE",
                records_ingested=0,
                details={"error": str(e), "error_type": type(e).__name__},
                db_path=self.db_path
            )
            raise

    def fetch_cpi_airfare_data(self, year: str = str(LATEST_BENCHMARK_YEAR), base_year: str = "2024") -> Dict[str, Any]:
        """
        Ingests official CPI Item 294 ('Airfare', code '07.3.3.1.2.01', Division 'Transport')
        across All India and States (Rural, Urban, Combined).
        """
        op_name = f"fetch_cpi_airfare_data_item294_y{year}"
        params = {
            "base_year": base_year,
            "year": year,
            "series": "Current",
            "item_code": "294"
        }

        try:
            raw_data = esankhyiki.get_data("CPI", params, format="dict")
            if isinstance(raw_data, list):
                data_list = raw_data
                meta_info = {}
            elif isinstance(raw_data, dict):
                data_list = raw_data.get("data", [])
                meta_info = raw_data.get("meta_data", {})
            else:
                data_list = []
                meta_info = {}

            inserted_count = insert_cpi_records(data_list, db_path=self.db_path)

            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation=op_name,
                status="SUCCESS",
                records_ingested=inserted_count,
                details={
                    "params": params,
                    "fetched_records": len(data_list),
                    "inserted_records": inserted_count,
                    "meta_data": meta_info
                },
                db_path=self.db_path
            )

            return {
                "status": "success",
                "item": "Airfare (Item 294 / 07.3.3.1.2.01)",
                "year": year,
                "base_year": base_year,
                "records_fetched": len(data_list),
                "records_saved": inserted_count,
                "sample_data": data_list[:3]
            }

        except Exception as e:
            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation=op_name,
                status="FAILURE",
                records_ingested=0,
                details={"params": params, "error": str(e), "error_type": type(e).__name__},
                db_path=self.db_path
            )
            raise

    def fetch_cpi_transport_group_data(self, year: str = "2024", base_year: str = "2012") -> Dict[str, Any]:
        """
        Ingests official 2012 Base Group/Subgroup level CPI data ('Transport and Communication').
        """
        op_name = f"fetch_cpi_transport_group_y{year}"
        params = {
            "base_year": base_year,
            "year": year,
            "series": "Current"
        }

        try:
            raw_data = esankhyiki.get_data("CPI", params, format="dict")
            if isinstance(raw_data, list):
                data_list = raw_data
            elif isinstance(raw_data, dict):
                data_list = raw_data.get("data", [])
            else:
                data_list = []

            # Filter for Transport & Communication subgroup
            transport_rows = [
                d for d in data_list
                if "transport" in str(d.get("subgroup", "")).lower() or "transport" in str(d.get("group", "")).lower()
            ]

            inserted_count = insert_cpi_records(transport_rows, db_path=self.db_path)

            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation=op_name,
                status="SUCCESS",
                records_ingested=inserted_count,
                details={
                    "params": params,
                    "total_fetched": len(data_list),
                    "transport_subgroup_records": len(transport_rows),
                    "inserted_records": inserted_count
                },
                db_path=self.db_path
            )

            return {
                "status": "success",
                "subgroup": "Transport and Communication (Base 2012)",
                "year": year,
                "base_year": base_year,
                "records_saved": inserted_count,
                "sample_data": transport_rows[:3]
            }


        except Exception as e:
            log_ingestion(
                source="MoSPI_eSankhyiki",
                operation=op_name,
                status="FAILURE",
                records_ingested=0,
                details={"params": params, "error": str(e), "error_type": type(e).__name__},
                db_path=self.db_path
            )
            raise

    def seed_official_press_release_benchmarks(self) -> Dict[str, Any]:
        """
        Seeds official MoSPI July 2026 benchmark press release figures (Base 2024=100)
        including General CPI, Group 07 Transport, and Group 07.3 Passenger transport services proxy.
        """
        records = [
            {
                "base_year": "2024",
                "series": "Current",
                "year": 2026,
                "month": "July",
                "state": "All India",
                "sector": "Combined",
                "division": "General",
                "group_name": "General",
                "item_name": "General CPI",
                "item_code": "00",
                "index": 107.94,
                "inflation": 4.45,
                "imputation": "P",
                "is_proxy": 0,
                "note": "MoSPI Press Release dated 12 Aug 2026 (Provisional)"
            },
            {
                "base_year": "2024",
                "series": "Current",
                "year": 2026,
                "month": "July",
                "state": "All India",
                "sector": "Combined",
                "division": "Transport",
                "group_name": "Transport",
                "item_name": "Group 07 Transport",
                "item_code": "07",
                "index": 105.63,
                "inflation": 4.43,
                "imputation": "P",
                "is_proxy": 0,
                "note": "MoSPI Press Release dated 12 Aug 2026 (Provisional)"
            },
            {
                "base_year": "2024",
                "series": "Current",
                "year": 2026,
                "month": "July",
                "state": "All India",
                "sector": "Combined",
                "division": "Transport",
                "group_name": "Passenger transport services",
                "sub_class": "Passenger transport by air, domestic",
                "item_name": "Airfare (Proxy: 07.3 Passenger transport services)",
                "item_code": "07.3.3.1.2.01",
                "index": 105.39,
                "inflation": 2.90,
                "imputation": "P",
                "is_proxy": 1,
                "note": "Group-level proxy for Item 294 from MoSPI Press Release dated 12 Aug 2026 (Provisional)"
            }
        ]
        inserted = insert_cpi_records(records, db_path=self.db_path)
        log_ingestion(
            source="MoSPI_Press_Release_Aug2026",
            operation="seed_official_press_release_benchmarks",
            status="SUCCESS",
            records_ingested=inserted,
            details={"benchmark_period": "July 2026", "source_date": "2026-08-12", "records_count": len(records)},
            db_path=self.db_path
        )
        return {
            "status": "success",
            "benchmark_period": "July 2026",
            "records_saved": inserted,
            "figures": OFFICIAL_MOSPI_JULY_2026
        }

