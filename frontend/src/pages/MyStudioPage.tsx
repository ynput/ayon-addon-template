import type { FC } from "react";
import { ProjectList, StudioPageLayout, useSlot, type SlotProps } from "@ynput/ayon-addon";
import { useMyAddonGetHelloQuery } from "@/api/my_addon";

// The page's content. It reads the projects picked in the list on the left from the slot's
// context: AYON keeps that selection, per page.
const SelectedProjects = () => {
  const { selectedProjects } = useSlot("studio.page");
  const { data, isLoading, error } = useMyAddonGetHelloQuery();

  return (
    <div style={{ padding: 16 }}>
      <h2>{isLoading ? "Loading..." : error ? "The addon's server didn't answer" : data?.message}</h2>
      <p>
        {selectedProjects.length
          ? `Selected projects: ${selectedProjects.join(", ")}`
          : "Select projects on the left."}
      </p>
    </div>
  );
};

// The studio page (studio.page slot, see src/manifest.ts). It gets its slot's context as props;
// components below it read the same context with useSlot("studio.page").
const MyStudioPage: FC<SlotProps<"studio.page">> = () => (
  <StudioPageLayout sidebar={<ProjectList multiSelect />}>
    <SelectedProjects />
  </StudioPageLayout>
);

export default MyStudioPage;
