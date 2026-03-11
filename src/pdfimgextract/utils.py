def fix_ext(ext: str) -> str:
    match ext:
        case "jpx":
            return "jpg"
        case _:
            return ext.lower()
