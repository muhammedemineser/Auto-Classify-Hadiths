import xml.etree.ElementTree as ET

tree = ET.parse("/home/mo/desk/apps/classify/chunks_with_most_isnad_elements2.xml")
root = tree.getroot()
print(root)
