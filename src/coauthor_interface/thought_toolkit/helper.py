def apply_text_operations(text, mask, ops, source, debug=False):
    original_text = text
    original_mask = mask
    new_text = ""
    new_mask = ""

    for i, op in enumerate(ops):
        if "retain" in op:
            num_char = op["retain"]
            if debug:
                print("@ Retain:", num_char)
            retain_text = original_text[:num_char]
            retain_mask = original_mask[:num_char]
            original_text = original_text[num_char:]
            original_mask = original_mask[num_char:]
            new_text = new_text + retain_text
            new_mask = new_mask + retain_mask

        elif "insert" in op:
            insert_text = op["insert"]
            if debug:
                print("@ Insert:", insert_text)
            if source == "api":
                # Use '*' for API insertions
                insert_mask = "*" * len(insert_text)
            else:
                # Use '_' for user insertions
                insert_mask = "_" * len(insert_text)

            if isinstance(insert_text, dict):
                if "image" in insert_text:
                    print("Skipping invalid object insertion (image)")
                else:
                    import ipdb

                    ipdb.set_trace()
                    print(insert_text)
            else:
                new_text = new_text + insert_text
                new_mask = new_mask + insert_mask

        elif "delete" in op:
            num_char = op["delete"]
            if debug:
                print("@ Delete:", num_char)
            if original_text:
                original_text = original_text[num_char:]
                original_mask = original_mask[num_char:]
            else:
                new_text = new_text[:-num_char]
                new_mask = new_mask[:-num_char]

        else:
            print("@ Unknown operation:", op)

        if debug:
            print("Document:", new_text + original_text, "\n")

    if debug:
        print("Final document:", new_text + original_text)

    return new_text + original_text, new_mask + original_mask


def apply_logs_to_writing(current_writing, current_mask, all_logs):
    for log in all_logs:
        if "textDelta" in log and "ops" in log["textDelta"]:
            ops = log["textDelta"]["ops"]
            source = log["eventSource"]
            current_writing, current_mask = apply_text_operations(current_writing, current_mask, ops, source)
    return current_writing, current_mask
