# JPype/JVM起動処理
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Sequence

from .errors import JVMStartError


def default_jar_path() -> Path:
    return Path(__file__).resolve().parent / "jars" / "nlp4j-localsearch.jar"


def extract_nested_jars(jar_path: Path) -> list[str]:
    """Extract nested JAR files from a Jar-in-Jar file to a temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="nlp4j_jars_"))
    extracted_jars = []
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('.jar'):
                    # Extract nested JAR to temp directory
                    extracted_path = temp_dir / file_info.filename
                    extracted_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zip_ref.open(file_info.filename) as source:
                        with open(extracted_path, 'wb') as target:
                            target.write(source.read())
                    
                    extracted_jars.append(str(extracted_path))
    except Exception as e:
        raise JVMStartError(f"Failed to extract nested JARs from {jar_path}") from e
    
    return extracted_jars


def ensure_jvm(
    classpath: Optional[Sequence[str | Path]] = None,
    jvm_args: Optional[Sequence[str]] = None,
) -> None:
    try:
        import jpype
        import jpype.imports  # noqa: F401
    except ImportError as e:
        raise JVMStartError(
            "jpype1 is required. Install it with: pip install jpype1"
        ) from e

    if jpype.isJVMStarted():
        return

    jar_path = default_jar_path()
    
    # Start with the main JAR
    cp = [str(jar_path)]
    
    # Extract and add nested JARs
    try:
        nested_jars = extract_nested_jars(jar_path)
        cp.extend(nested_jars)
    except Exception as e:
        raise JVMStartError(f"Failed to process JAR file: {jar_path}") from e
    
    # Add user-specified classpath
    if classpath:
        cp.extend(str(Path(p)) for p in classpath)

    args = list(jvm_args or [])

    try:
        jpype.startJVM(*args, classpath=cp)
    except Exception as e:
        raise JVMStartError(f"Failed to start JVM. classpath={cp}") from e