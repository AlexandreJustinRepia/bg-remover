from rembg import remove, new_session

# High quality model
session = new_session("isnet-general-use")


def remove_background(input_path):
    with open(input_path, "rb") as f:
        input_data = f.read()

    output = remove(input_data, session=session)

    return output