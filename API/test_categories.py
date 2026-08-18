from ml.predictor import _model

model = _model()
booster = model.get_booster()

categories = booster.get_categories(export_to_arrow=True)

print("TYPE :", type(categories))
print("FEATURES :", booster.feature_names)

try:
    arrow = categories.to_arrow()
    print("ARROW TYPE :", type(arrow))
    print("ARROW :", arrow)
except Exception as e:
    print("ERREUR to_arrow() :", repr(e))