"""Parsers for supported lockfile formats used by the CLI wrapper."""

import json
import logging
import sys
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from cyclonedx.model.bom import Bom as CycloneDxBom

try:  # Python >=3.11
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python 3.10 fallback
    import tomli as tomllib  # type: ignore[assignment]  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a package dependency with coordinate information."""

    type: str  # Package type: "pypi", "crate", "npm", "maven"
    registry: str  # Registry: "pypi", "cratesio", "npmjs", "mavencentral"
    name: str  # Package name
    version: str  # Package version
    license: str | None = None  # SPDX license expression if available

    def to_coordinate(self) -> str:
        """Convert to dash-licenses coordinate format."""
        return f"{self.type}/{self.registry}/-/{self.name}/{self.version}"


def parse(file: Path) -> list[Dependency]:
    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"
    if not file.exists():
        sys.exit(f"lockfile not found: {file}")

    # TODO: sync typical filenames with e.g. dependabot definitions
    if file.stem.startswith("requirements") and file.suffix in (".txt", ".out"):
        return parse_pypi(file)
    elif file.name == "Cargo.lock":
        return parse_crate(file)
    elif file.name == "uv.lock":
        return parse_uv_lock(file)
    elif file.suffix == ".json" and (
        "cdx" in file.name.lower() or "cyclonedx" in file.name.lower()
    ):
        return parse_cdx(file)
    elif file.suffix == ".json" and "spdx" in file.name.lower():
        return parse_spdx(file)
    else:
        sys.exit(f"Unsupported lockfile type: {file}")


def read_file_lines(file: Path) -> Generator[str, None, None]:
    """Yield non-empty, non-comment lines from a text file."""
    text = file.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def parse_pypi(file: Path) -> list[Dependency]:
    """Parse a pip requirements file into dash-licenses dependency coordinates."""
    deps: list[Dependency] = []

    for line in read_file_lines(file):
        # Skip --hash lines (they're options for the previous requirement)
        if line.startswith("--hash="):
            continue

        if "==" in line:
            name, _, version = line.strip("\\ ").partition("==")
            deps.append(
                Dependency(type="pypi", registry="pypi", name=name, version=version)
            )
        else:
            logger.warning(f"Skipping unsupported pip requirement line: {line}")

    return deps


def parse_crate(file: Path) -> list[Dependency]:
    """Parse a Cargo.lock and extract crates.io dependencies."""
    deps: list[Dependency] = []

    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"

    try:
        data = cast(
            "dict[str, object]", tomllib.loads(file.read_text(encoding="utf-8"))
        )
    except Exception as exc:  # pragma: no cover - defensive error surface
        raise ValueError(f"Failed to parse Cargo.lock as TOML: {file}") from exc

    packages = data.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("Invalid Cargo.lock: 'package' section missing or malformed")

    for pkg in packages:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(pkg, dict):
            continue
        pkg = cast("dict[str, object]", pkg)

        name = pkg.get("name")
        version = pkg.get("version")
        source = pkg.get("source", "") or ""

        if not (name and version):
            continue

        # Only crates.io is supported today; detect via presence of 'crates' in source.
        if source and "crates" not in str(source).lower():
            raise ValueError(f"Unknown crate registry source: {source}")

        deps.append(
            Dependency(
                type="crate", registry="cratesio", name=str(name), version=str(version)
            )
        )

    return deps


def parse_uv_lock(file: Path) -> list[Dependency]:
    """Parse Python project dependencies from uv.lock.

    Extracts pinned package versions from the uv lockfile format.
    Only includes packages from PyPI registry.
    """
    deps: list[Dependency] = []

    assert isinstance(file, Path), f"Expected Path, got <{type(file)}> {file}"

    try:
        data = cast("dict[str, Any]", tomllib.loads(file.read_text(encoding="utf-8")))
    except Exception as exc:  # pragma: no cover - defensive error surface
        raise ValueError(f"Failed to parse {file.name} as TOML: {file}") from exc

    packages = data.get("package", [])
    if not isinstance(packages, list):
        logger.warning("Invalid uv.lock: 'package' section missing or malformed")
        return deps

    for pkg in packages:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(pkg, dict):
            continue
        pkg = cast("dict[str, Any]", pkg)

        name = pkg.get("name")
        version = pkg.get("version")
        source = pkg.get("source", {})

        if not (name and version):
            continue

        # Only include packages from PyPI registry (default source)
        if isinstance(source, dict):
            source = cast("dict[str, Any]", source)
            registry = source.get("registry", "https://pypi.org/simple")
            # Only include PyPI packages; skip other registries
            if registry and "pypi.org" not in registry:
                logger.debug(
                    f"Skipping package from non-PyPI registry: {name} from {registry}"
                )
                continue

        deps.append(
            Dependency(
                type="pypi", registry="pypi", name=str(name), version=str(version)
            )
        )
    return deps


def _purl_to_dependency(purl: str, license: str | None = None) -> Dependency | None:
    """Convert a Package URL (purl) to a Dependency object.

    Examples:
        pkg:cargo/serde@1.0.228 -> Dependency(type="crate", registry="cratesio", name="serde", version="1.0.228")
        pkg:pypi/requests@2.32.3 -> Dependency(type="pypi", registry="pypi", name="requests", version="2.32.3")
        pkg:npm/express@4.18.2 -> Dependency(type="npm", registry="npmjs", name="express", version="4.18.2")
    """
    if not purl or not purl.startswith("pkg:"):
        return None

    try:
        # Remove pkg: prefix
        purl = purl[4:]

        # Split into type and rest
        type_part, _, rest = purl.partition("/")

        # Extract name and version
        if "@" not in rest:
            return None
        name_part, version = rest.rsplit("@", 1)

        # Remove any qualifiers or subpath
        version = version.split("?")[0].split("#")[0]
        name = name_part.split("/")[-1]  # Take last part for namespaced packages

        # Map purl type to Dependency object
        if type_part == "cargo":
            return Dependency(
                type="crate",
                registry="cratesio",
                name=name,
                version=version,
                license=license,
            )
        elif type_part == "pypi":
            return Dependency(
                type="pypi",
                registry="pypi",
                name=name,
                version=version,
                license=license,
            )
        elif type_part == "npm":
            return Dependency(
                type="npm",
                registry="npmjs",
                name=name,
                version=version,
                license=license,
            )
        elif type_part == "maven":
            # Maven format needs group/artifact mapping
            if "/" in name_part:
                group, artifact = name_part.rsplit("/", 1)
                # For maven, we include group in the name for now
                return Dependency(
                    type="maven",
                    registry="mavencentral",
                    name=f"{group}/{artifact}",
                    version=version,
                    license=license,
                )
            return Dependency(
                type="maven",
                registry="mavencentral",
                name=name,
                version=version,
                license=license,
            )
        else:
            logger.debug(f"Unsupported purl type: {type_part}")
            return None
    except Exception as e:
        logger.warning(f"Failed to parse purl '{purl}': {e}")
        return None


def parse_cdx(file: Path) -> list[Dependency]:  # noqa: C901
    """Parse a CycloneDX SBOM JSON file and extract dependency coordinates.

    Extracts package URLs (purls) from components and converts them to
    dash-licenses coordinate format. Uses the official cyclonedx-python-lib.
    """
    deps: list[Dependency] = []

    try:
        json_data = json.loads(file.read_text(encoding="utf-8"))
        bom: CycloneDxBom = CycloneDxBom.from_json(json_data)  # type: ignore[attr-defined,assignment]
    except Exception as exc:
        logger.warning(f"Failed to parse CycloneDX SBOM from {file}: {exc}")
        return deps

    if not bom.components:  # type: ignore[union-attr]
        logger.debug(f"No components found in CycloneDX SBOM: {file}")
        return deps

    for component in bom.components:  # type: ignore[union-attr]
        if not component.purl:
            continue

        purl_str = str(component.purl)

        # Extract license if available
        original_license = None
        if component.licenses:
            # Get the first license (DisjunctiveLicense object)
            license_obj = next(iter(component.licenses), None)  # type: ignore[arg-type]
            if license_obj:
                # DisjunctiveLicense has id and name attributes directly
                if hasattr(license_obj, "id") and license_obj.id:  # type: ignore[union-attr]
                    original_license = _normalize_license_expression(license_obj.id)
                elif hasattr(license_obj, "name") and license_obj.name:
                    original_license = _normalize_license_expression(license_obj.name)

        dep = _purl_to_dependency(purl_str, license=original_license)
        if dep:
            deps.append(dep)
            if original_license:
                logger.debug(
                    f"Found license for {dep.to_coordinate()}: {original_license}"
                )

    return deps


def _normalize_license_expression(license_str: str) -> str:
    """Normalize license expressions to follow SPDX standards.

    Some SBOM generators use non-standard separators like '/' instead of 'OR'.
    This function normalizes common issues to make expressions SPDX-compliant.

    Args:
        license_str: The license expression to normalize

    Returns:
        Normalized license expression following SPDX standards

    Examples:
        "MIT/Apache-2.0" -> "MIT OR Apache-2.0"
        "Apache-2.0/MIT" -> "Apache-2.0 OR MIT"
    """
    if not license_str or license_str in ("NOASSERTION", "NONE"):
        return license_str

    # Replace '/' with ' OR ' if it's not already using proper SPDX operators
    # This handles common non-standard dual-license notation like "MIT/Apache-2.0"
    if "/" in license_str and " OR " not in license_str and " AND " not in license_str:  # noqa: SIM102
        # Only normalize if this looks like a license expression (contains typical license keywords)
        if any(
            keyword in license_str
            for keyword in ["MIT", "Apache", "GPL", "BSD", "LGPL", "MPL"]
        ):
            logger.debug(
                f"Normalizing non-standard license expression: '{license_str}'"
            )
            normalized = license_str.replace("/", " OR ")
            logger.debug(f"  Normalized to: '{normalized}'")
            return normalized

    return license_str


def parse_spdx(file: Path) -> list[Dependency]:  # noqa: C901
    """Parse an SPDX SBOM JSON file and extract dependency coordinates.

    Extracts package URLs (purls) from package externalRefs and converts them
    to dash-licenses coordinate format. Uses lenient JSON parsing to handle
    non-standard license expressions.
    """
    deps: list[Dependency] = []

    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to parse SPDX JSON from {file}: {exc}")
        return deps

    # Validate it's an SPDX file
    if not data.get("spdxVersion", "").startswith("SPDX-"):
        logger.warning(f"Invalid SPDX format in {file}")
        return deps

    packages = data.get("packages", [])
    if not isinstance(packages, list):
        logger.warning(f"Invalid SPDX structure in {file}: packages not a list")
        return deps

    for package in packages:
        if not isinstance(package, dict):
            continue

        # Skip the root package
        spdx_id = cast("str", package.get("SPDXID", ""))
        if spdx_id in ("SPDXRef-DOCUMENT", "SPDXRef-RootPackage"):
            continue

        # Extract purl from externalRefs
        purl: str | None = None
        external_refs = package.get("externalRefs", [])
        if isinstance(external_refs, list):
            for ref in external_refs:
                if not isinstance(ref, dict):
                    continue
                if ref.get("referenceType") == "purl":
                    purl = cast("str | None", ref.get("referenceLocator"))
                    break

        if not purl:
            continue

        # Extract license if available
        original_license: str | None = None
        license_concluded = cast("str | None", package.get("licenseConcluded"))
        license_declared = cast("str | None", package.get("licenseDeclared"))

        # Prefer licenseConcluded, fall back to licenseDeclared
        # Skip NOASSERTION values and normalize the expression
        if license_concluded and license_concluded not in ("NOASSERTION", "NONE"):
            original_license = _normalize_license_expression(license_concluded)
        elif license_declared and license_declared not in ("NOASSERTION", "NONE"):
            original_license = _normalize_license_expression(license_declared)

        dep = _purl_to_dependency(purl, license=original_license)
        if dep:
            deps.append(dep)
            if original_license:
                logger.debug(
                    f"Found license for {dep.to_coordinate()}: {original_license}"
                )

    return deps
