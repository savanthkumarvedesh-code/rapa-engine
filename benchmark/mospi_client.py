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
from data.db import insert_cpi_records, log_ingestion, DB_PATH, init_db


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

    def fetch_cpi_airfare_data(self, year: str = "2025", base_year: str = "2024") -> Dict[str, Any]:
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
