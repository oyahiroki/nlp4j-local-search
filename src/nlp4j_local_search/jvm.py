# JPype/JVM起動処理
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Sequence

from .errors import JVMStartError


def default_jar_path() -> Path:
    return Path(__file__).resolve().parent / "jars" / "0.6.0" / "nlp4j-localsearch.jar"


def extract_jar_contents(jar_path: Path) -> tuple[list[str], str]:
    """Extract nested JAR files and resources from a Jar-in-Jar file.

    Returns:
        (list of extracted .jar paths, path to the resources root directory)

    Nested .jar files are placed flat inside the temp directory.
    Files under ``resources/`` are extracted to the *root* of a separate
    resources temp directory so that ``getResourceAsStream("/filename.bin")``
    can find them on the classpath.
    """
    jars_dir = Path(tempfile.mkdtemp(prefix="nlp4j_jars_"))
    res_dir = Path(tempfile.mkdtemp(prefix="nlp4j_res_"))
    extracted_jars = []

    try:
        with zipfile.ZipFile(jar_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                name = file_info.filename

                # ネストした JAR → jars_dir 以下に展開
                if name.endswith('.jar'):
                    extracted_path = jars_dir / name
                    extracted_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(name) as src, open(extracted_path, 'wb') as dst:
                        dst.write(src.read())
                    extracted_jars.append(str(extracted_path))

                # resources/ 内ファイル → res_dir のルート直下に展開
                # Java: getResourceAsStream("/opennlp-en-ud-ewt-tokens-1.3-2.5.4.bin")
                elif name.startswith('resources/') and not name.endswith('/'):
                    basename = Path(name).name
                    extracted_path = res_dir / basename
                    with zip_ref.open(name) as src, open(extracted_path, 'wb') as dst:
                        dst.write(src.read())

    except Exception as e:
        raise JVMStartError(f"Failed to extract JAR contents from {jar_path}") from e

    return extracted_jars, str(res_dir)


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

    # Extract nested JARs and resources; add both to the classpath
    try:
        nested_jars, res_dir = extract_jar_contents(jar_path)
        cp.extend(nested_jars)
        cp.append(res_dir)   # makes getResourceAsStream("/filename.bin") work
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