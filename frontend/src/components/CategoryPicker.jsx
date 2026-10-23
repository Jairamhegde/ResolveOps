import { CATEGORIES } from "../format";

// A super admin's category filter. An empty value means every category.
function CategoryPicker({ value, onChange }) {
  return (
    <label className="field">
      Category
      <select className="field-control" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All categories</option>
        {CATEGORIES.map((category) => (
          <option key={category.value} value={category.value}>
            {category.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default CategoryPicker;
