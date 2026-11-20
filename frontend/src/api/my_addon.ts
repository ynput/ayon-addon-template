// my_addon's server endpoints. They are generated into ./generated/my_addon.ts by
// `ayon-addon generate-rest`: never edit that file, change them here instead (cache tags,
// transformResponse, optimistic updates). generate-rest offers to add the hooks of new endpoints.
import { myAddonRestApi } from "./generated/my_addon";

export const myAddonApi = myAddonRestApi.enhanceEndpoints({
  addTagTypes: [],
  endpoints: {},
});

export const {
  useMyAddonGetHelloQuery,
} = myAddonApi;
