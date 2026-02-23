
import sys
input_file = sys.argv[1] if len(sys.argv) > 1 else 'debug_out_3.txt'
output_file = sys.argv[2] if len(sys.argv) > 2 else 'debug_out_3_utf8.txt'

try:
    with open(input_file, 'r', encoding='utf-16') as f:
        content = f.read()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Converted {input_file} to {output_file} successfully.")
except Exception as e:
    print(f"Error converting: {e}")
