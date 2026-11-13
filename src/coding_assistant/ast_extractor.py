from pathlib import Path

try:
    import tree_sitter_python as tspy
    import tree_sitter_javascript as tsjs
    import tree_sitter_typescript as tsts
    import tree_sitter_cpp as tscpp
    from tree_sitter import Language, Parser, Query, QueryCursor
    TREE_SITTER_AVAILABLE=True
except ImportError:
    TREE_SITTER_AVAILABLE=False

if TREE_SITTER_AVAILABLE:
    LANGUAGES={
        ".py":Language(tspy.language()),
        ".js":Language(tsjs.language()),
        ".jsx":Language(tsjs.language()),
        ".ts":Language(tsts.language_typescript()),
        ".tsx":Language(tsts.language_tsx()),
        ".cpp":Language(tscpp.language()),
        ".cc":Language(tscpp.language()),
        ".c":Language(tscpp.language()),
        ".h":Language(tscpp.language()),
        ".hpp":Language(tscpp.language()),
    }

    QUERIES={
        ".py":"""
            (class_definition) @class
            (function_definition) @function
            (import_statement) @import
            (import_from_statement) @import
        """,
        ".js":"""
            (class_declaration) @class
            (function_declaration) @function
            (lexical_declaration
                (variable_declarator
                    name: (identifier) @arrow_func
                    value: (arrow_function)))
            (export_statement) @export
        """,
        ".ts":"""
            (class_declaration) @class
            (function_declaration) @function
            (interface_declaration) @interface
            (type_alias_declaration) @type_alias
            (lexical_declaration
                (variable_declarator
                    name: (identifier) @arrow_func
                    value: (arrow_function)))
        """,
        ".cpp":"""
            (class_specifier) @class
            (struct_specifier) @struct
            (function_definition) @function
            (preproc_include) @include
        """,
    }

    QUERY_MAP={
        ".py":".py",
        ".js":".js",
        ".jsx":".js",
        ".ts":".ts",
        ".tsx":".ts",
        ".cpp":".cpp",
        ".cc":".cpp",
        ".c":".cpp",
        ".h":".cpp",
        ".hpp":".cpp",
    }

def get_file_summary(file_path: str)->str:
    ext=Path(file_path).suffix
    
    if not TREE_SITTER_AVAILABLE or ext not in LANGUAGES:
        try:
            with open(file_path,"r",errors="ignore") as f:
                lines=f.readlines()[:40]
            return f"File: {file_path} (first 40 lines)\n{''.join(lines)}\n"
        except Exception:
            return f"File: {file_path} (could not read)\n"
            
    try:
        with open(file_path,"rb") as f:
            source=f.read()
            
        language=LANGUAGES[ext]
        parser=Parser(language)
        tree=parser.parse(source)
        
        query_key=QUERY_MAP[ext]
        query=Query(language, QUERIES[query_key])
        cursor=QueryCursor(query)
        captures=cursor.captures(tree.root_node)
        
        results=[f"File: {file_path}"]
        
        if isinstance(captures,dict):
            for tag,nodes in captures.items():
                for node in nodes:
                    if node.text:
                        first_line=node.text.decode("utf-8").split("\n")[0].strip()
                        results.append(f"  [{tag}] {first_line}")
                
        return "\n".join(results)+"\n"
        
    except Exception as e:
        return f"File: {file_path} (parse error: {e})\n"

if __name__ == "__main__":
    print(get_file_summary("pyproject.toml")) # for test
