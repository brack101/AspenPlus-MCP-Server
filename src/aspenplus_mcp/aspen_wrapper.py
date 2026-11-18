"""Wrapper for Aspen Plus COM interface."""

import logging
from typing import TYPE_CHECKING, Any, Optional
import sys

if TYPE_CHECKING:
    from .enhanced import EnhancedSession

logger = logging.getLogger(__name__)

ASPEN_PROGID = "Apwn.Document"


class AspenPlusWrapper:
    """Wrapper class for Aspen Plus COM automation with extended capabilities.

    - Basic mode: direct COM access via pywin32 (node paths only)
    - Enhanced mode: flowsheet editing via py2aspen (see enhanced.py)
    """

    def __init__(self):
        """Initialize the Aspen Plus wrapper."""
        self.aspen = None
        self.session: Optional["EnhancedSession"] = None  # enhanced mode (py2aspen)
        self._is_windows = sys.platform == "win32"
        self._current_file = None

        if self._is_windows:
            try:
                import win32com.client

                self.win32com = win32com.client
                logger.info("Windows COM interface available")
            except ImportError:
                logger.warning("pywin32 not installed - Aspen Plus connection unavailable")
                self.win32com = None
        else:
            logger.warning("Not running on Windows - Aspen Plus connection unavailable")
            self.win32com = None

    def connect(self) -> bool:
        """
        Connect to Aspen Plus application.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.win32com:
            raise RuntimeError("Cannot connect to Aspen Plus: pywin32 not available")

        try:
            self.aspen = self.win32com.Dispatch(ASPEN_PROGID)
            logger.info("Connected to Aspen Plus")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Aspen Plus: {e}")
            raise

    def open_file(self, filepath: str, use_enhanced: bool = False) -> bool:
        """
        Open an Aspen Plus simulation file.

        Args:
            filepath: Path to .bkp or .apw file
            use_enhanced: Use the enhanced interface with additional capabilities

        Returns:
            bool: True if file opened successfully
        """
        if use_enhanced and self._is_windows:
            try:
                # Imported lazily: py2aspen/comtypes are Windows-only
                from .enhanced import EnhancedSession

                self.session = EnhancedSession(ASPEN_PROGID, filepath)
                # Share the session's COM document so node-path tools
                # (get_value, set_value) also work in enhanced mode
                self.aspen = self.session.app
                self._current_file = filepath
                logger.info(f"Opened file with enhanced interface: {filepath}")
                return True
            except Exception as e:
                self.session = None
                logger.warning(f"Failed to use enhanced interface, falling back to basic: {e}")
                use_enhanced = False

        if not use_enhanced:
            if not self.aspen:
                self.connect()

            try:
                self.aspen.InitFromArchive2(filepath)
                self._current_file = filepath
                logger.info(f"Opened file: {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to open file {filepath}: {e}")
                raise

    def close(self):
        """Close the Aspen Plus connection."""
        if self.session:
            try:
                self.session.close()
                logger.info("Closed Aspen Plus connection (enhanced interface)")
            except Exception as e:
                logger.error(f"Error closing Aspen Plus: {e}")
            finally:
                self.session = None
                # self.aspen is the session's document in enhanced mode - already closed
                self.aspen = None

        if self.aspen:
            try:
                self.aspen.Close()
                logger.info("Closed Aspen Plus connection")
            except Exception as e:
                logger.error(f"Error closing Aspen Plus: {e}")
            finally:
                self.aspen = None

        self._current_file = None

    def run_simulation(self) -> bool:
        """
        Run the current simulation.

        Returns:
            bool: True if simulation ran successfully
        """
        if self.session:
            try:
                self.session.run()
                logger.info("Simulation completed (enhanced interface)")
                return True
            except Exception as e:
                logger.error(f"Simulation failed: {e}")
                raise

        if not self.aspen:
            raise RuntimeError("No Aspen Plus file is open")

        try:
            # Run simulation with engine 2 (recommended for automation)
            self.aspen.Engine.Run2()
            logger.info("Simulation completed")
            return True
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise

    def get_value(self, path: str) -> Any:
        """
        Get a value from the simulation using a node path.

        Args:
            path: Node path (e.g., r"\\Data\\Streams\\S1\\Output\\TEMP_OUT\\MIXED\\MIXED")

        Returns:
            Value at the specified path
        """
        if not self.aspen:
            raise RuntimeError("No Aspen Plus file is open")

        try:
            node = self.aspen.Tree.FindNode(path)
            return node.Value
        except Exception as e:
            logger.error(f"Failed to get value at {path}: {e}")
            raise

    def set_value(self, path: str, value: Any) -> bool:
        """
        Set a value in the simulation using a node path.

        Args:
            path: Node path
            value: Value to set

        Returns:
            bool: True if value set successfully
        """
        if not self.aspen:
            raise RuntimeError("No Aspen Plus file is open")

        try:
            node = self.aspen.Tree.FindNode(path)
            node.Value = value
            logger.info(f"Set value at {path} to {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set value at {path}: {e}")
            raise

    # Enhanced methods (py2aspen)
    def _require_session(self) -> "EnhancedSession":
        if not self.session:
            raise RuntimeError("Enhanced interface not available. Open file with use_enhanced=True")
        return self.session

    def place_block(self, block_name: str, equipment_type: str) -> bool:
        """
        Place a new block in the flowsheet (enhanced interface only).

        Args:
            block_name: Name for the block
            equipment_type: Type of equipment (e.g., "Mixer", "Heater", "Flash2")

        Returns:
            bool: True if block placed successfully
        """
        session = self._require_session()
        try:
            session.place_block(block_name, equipment_type)
            logger.info(f"Placed block {block_name} of type {equipment_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to place block: {e}")
            raise

    def delete_block(self, block_name: str) -> bool:
        """
        Delete a block from the flowsheet (enhanced interface only).

        Args:
            block_name: Name of the block to delete

        Returns:
            bool: True if block deleted successfully
        """
        session = self._require_session()
        try:
            session.delete_block(block_name)
            logger.info(f"Deleted block {block_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete block: {e}")
            raise

    def place_stream(self, stream_name: str, stream_type: str = "MATERIAL") -> bool:
        """
        Place a new stream in the flowsheet (enhanced interface only).

        Args:
            stream_name: Name for the stream
            stream_type: Type of stream ("MATERIAL", "HEAT", "WORK", "POWER")

        Returns:
            bool: True if stream placed successfully
        """
        session = self._require_session()
        try:
            session.place_stream(stream_name, stream_type)
            logger.info(f"Placed stream {stream_name} of type {stream_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to place stream: {e}")
            raise

    def connect_stream(self, block_name: str, stream_name: str, port_name: str) -> bool:
        """
        Connect a stream to a block port (enhanced interface only).

        Args:
            block_name: Name of the block
            stream_name: Name of the stream
            port_name: Aspen port name on the block (e.g. "F(IN)", "P(OUT)")

        Returns:
            bool: True if connection successful
        """
        session = self._require_session()
        try:
            session.connect_stream(block_name, stream_name, port_name)
            logger.info(f"Connected stream {stream_name} to {block_name}.{port_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect stream: {e}")
            raise

    def save_simulation(self, filename: Optional[str] = None) -> bool:
        """
        Save the simulation (enhanced interface only).

        Args:
            filename: Optional new filename (.bkp = backup archive, otherwise
                Aspen document). If None, saves to current file.

        Returns:
            bool: True if save successful
        """
        session = self._require_session()
        try:
            session.save(filename)
            logger.info(f"Saved simulation as {filename}" if filename else "Saved simulation")
            return True
        except Exception as e:
            logger.error(f"Failed to save simulation: {e}")
            raise
