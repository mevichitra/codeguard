# Ground-truth check

For each finding, decide whether the old and the new finding are the **same**
issue (for an introduced finding: whether it is **new** in this commit), and write
`same`, `different` or `unclear` in the `verdict` column of `sample.csv`.
The harness's answer is given under *Truth*; judge the code, not the answer.

## 1. arches: `CG-QUAL-101` (edited)

- Commit: [403c462649](https://github.com/archesproject/arches/commit/403c4626495b979fe831a8f0baf6d8577708e3d7), file `arches/app/media/js/views/resource/edit-log.js`
- Truth: **known (edited)**, old line 58, new line 61
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    54                  }
    55                  full_value[k] = {new_value: v};
    56                  if (edit.card) {
    57                      _.each(edit.card.nodes, function(node){
>   58                          if (k == node.nodeid) {
    59                              full_value[node.nodeid].node = node;
    60                          }
    61                      }, this);
    62                  }
```
After:

```
    57                  }
    58                  full_value[nodeid] = {new_value: val, is_array: is_array};
    59                  if (edit.card) {
    60                      _.each(edit.card.nodes, function(node){
>   61                          if (nodeid == node.nodeid) {
    62                              full_value[node.nodeid].node = node;
    63                          }
    64                      }, this);
    65                  }
```

Diff near the line:

```diff
@@ -48,20 +50,21 @@ var ResourceEditLogView = BaseManagerView.extend({
                 return value;
             }

-            _.each(value, function(v, k){
-                if (_.isObject(v) && v['features']) {
-                    v = _.map(v['features'], function(feature){return JSON.stringify(feature['geometry'], rounder, 4);});
+            _.each(value, function(val, nodeid){
+                var is_array = _.isArray(val);
+                if (_.isObject(val) && val['features']) {
+                    val = _.map(val['features'], function(feature){return JSON.stringify(feature['geometry'], rounder, 4);});
                 }
-                full_value[k] = {new_value: v};
+                full_value[nodeid] = {new_value: val, is_array: is_array};
                 if (edit.card) {
                     _.each(edit.card.nodes, function(node){
-                        if (k == node.nodeid) {
+                        if (nodeid == node.nodeid) {
                             full_value[node.nodeid].node = node;
                         }
                     }, this);
                 }
             });
-            return _.map(full_value, function(v,k){return v;});   // eslint-disable-line @typescript-eslint/no-unused-vars
+            return _.map(full_value, function(val,nodeid){return val;});   // eslint-disable-line @typescript-eslint/no-unused-vars
         };

         _.each(edits, function(edit){
```

## 2. healthchecks: `CG-QUAL-104` (edited)

- Commit: [b83e3791d6](https://github.com/healthchecks/healthchecks/commit/b83e3791d6e2c276a13c0b40c2e435c6ec01125c), file `static/js/checks.js`
- Truth: **known (edited)**, old line 13, new line 13
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new)

Before:

```
     9          $("#update-name-form").attr("action", url);
    10          $("#update-name-input").val(this.dataset.name);
    11          $("#update-slug-input").val(this.dataset.slug);
    12
>   13          var tagsSelectize = document.getElementById("update-tags-input").selectize;
    14          tagsSelectize.setValue(this.dataset.tags.split(" "));
    15
    16          $("#update-desc-input").val(this.dataset.desc);
    17          $("#update-name-modal").modal("show");
```
After:

```
     9          $("#update-name-form").attr("action", url);
    10          $("#update-name-input").val(this.dataset.name);
    11          $("#update-slug-input").val(this.dataset.slug);
    12
>   13          var tagsTs = document.getElementById("update-tags-input").tomselect;
    14          tagsTs.setValue(this.dataset.tags.split(" "));
    15
    16          $("#update-desc-input").val(this.dataset.desc);
    17          $("#update-name-modal").modal("show");
```

Diff near the line:

```diff
@@ -10,8 +10,8 @@ $(function () {
         $("#update-name-input").val(this.dataset.name);
         $("#update-slug-input").val(this.dataset.slug);

-        var tagsSelectize = document.getElementById("update-tags-input").selectize;
-        tagsSelectize.setValue(this.dataset.tags.split(" "));
+        var tagsTs = document.getElementById("update-tags-input").tomselect;
+        tagsTs.setValue(this.dataset.tags.split(" "));

         $("#update-desc-input").val(this.dataset.desc);
         $("#update-name-modal").modal("show");
```

## 3. documenso: `CG-PERF-101` (edited)

- Commit: [9c27ce6d18](https://github.com/documenso/documenso/commit/9c27ce6d185f7e25eec80439b931c4709723a2ae), file `packages/app-tests/e2e/teams/team-documents.spec.ts`
- Truth: **known (edited)**, old line 37, new line 29
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    33
    34      // Check counts after filtering.
    35      await checkDocumentTabCount(page, 'Inbox', 0);
    36      await checkDocumentTabCount(page, 'Pending', 2);
>   37      await checkDocumentTabCount(page, 'Completed', 0);
    38      await checkDocumentTabCount(page, 'Draft', 1);
    39      await checkDocumentTabCount(page, 'All', 3);
    40
    41      await apiSignout({ page });
```
After:

```
    25      // Apply filter.
    26      await toggleDocumentSenderFilter(page, teamMember2.name ?? '');
    27
    28      // Check counts after filtering.
>   29      await checkDocumentCounts(page, { inbox: 0, pending: 2, completed: 0, draft: 1, all: 3 });
    30
    31      await apiSignout({ page });
    32    }
    33  });
```

Diff near the line:

```diff
@@ -20,23 +20,13 @@ test('[TEAMS]: check team documents count', async ({ page }) => {
     });

     // Check document counts.
-    await checkDocumentTabCount(page, 'Inbox', 0);
-    await checkDocumentTabCount(page, 'Pending', 2);
-    await checkDocumentTabCount(page, 'Completed', 1);
-    await checkDocumentTabCount(page, 'Draft', 2);
-    await checkDocumentTabCount(page, 'All', 5);
+    await checkDocumentCounts(page, { inbox: 0, pending: 2, completed: 1, draft: 2, all: 5 });

     // Apply filter.
-    await page.locator('button').filter({ hasText: 'Sender: All' }).click();
-    await page.getByRole('option', { name: teamMember2.name ?? '' }).click();
-    await page.waitForURL(/senderIds/);
+    await toggleDocumentSenderFilter(page, teamMember2.name ?? '');

     // Check counts after filtering.
-    await checkDocumentTabCount(page, 'Inbox', 0);
-    await checkDocumentTabCount(page, 'Pending', 2);
-    await checkDocumentTabCount(page, 'Completed', 0);
-    await checkDocumentTabCount(page, 'Draft', 1);
-    await checkDocumentTabCount(page, 'All', 3);
+    await checkDocumentCounts(page, { inbox: 0, pending: 2, completed: 0, draft: 1, all: 3 });

     await apiSignout({ page });
   }
```

## 4. pgadmin: `CG-QUAL-101` (edited)

- Commit: [5f56805162](https://github.com/pgadmin-org/pgadmin4/commit/5f56805162c117ac1de17368ef8fdc0b07221e2c), file `web/pgadmin/tools/sqleditor/static/js/components/QueryToolComponent.jsx`
- Truth: **known (edited)**, old line 713, new line 749
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
   709          for (const connItem of newConnList) {
   710            if(newConnData.sid == connItem.sid
   711              && newConnData.did == connItem.did
   712              && newConnData.user == connItem.user
>  713              && newConnData.role == connItem.role) {
   714              connItem.is_selected = true;
   715            } else {
   716              connItem.is_selected = false;
   717            }
```
After:

```
   745          for (const connItem of newConnList) {
   746            if(newConnData.sid == connItem.sid
   747              && newConnData.did == connItem.did
   748              && newConnData.user == connItem.user
>  749              && (newConnData.role || null) == (connItem.role || null)) {
   750              connItem.is_selected = true;
   751            } else {
   752              connItem.is_selected = false;
   753            }
```

Diff near the line:

```diff
@@ -702,15 +735,18 @@ export default function QueryToolComponent({params, pgWindow, pgAdmin, selectedN
     const selectConn = (newConnData, connected=false, obtainingConn=true)=>{
       setQtStatePartial((prevQtState)=>{
         let newConnList = [...prevQtState.connection_list];
-        /* If new, add to the list */
-        if(isNew) {
+        /* If new, add to the list if not already present */
+        if(isNew && !newConnList.some((c)=>c.sid == newConnData.sid
+          && c.did == newConnData.did
+          && c.user == newConnData.user
+          && (c.role || null) == (newConnData.role || null))) {
           newConnList.push(newConnData);
         }
         for (const connItem of newConnList) {
           if(newConnData.sid == connItem.sid
             && newConnData.did == connItem.did
             && newConnData.user == connItem.user
-            && newConnData.role == connItem.role) {
+            && (newConnData.role || null) == (connItem.role || null)) {
             connItem.is_selected = true;
           } else {
             connItem.is_selected = false;
```

## 5. openlibrary: `CG-QUAL-104` (edited)

- Commit: [53015559eb](https://github.com/internetarchive/openlibrary/commit/53015559ebcd126850e7b07792ebc7bcfa847919), file `openlibrary/plugins/openlibrary/js/jsdef.js`
- Truth: **known (edited)**, old line 77, new line 80
- Schemes that disagree with the truth: `github` (false_new), `line_text` (false_new)

Before:

```
    73      this.index0 = -1;
    74  }
    75
    76  ForLoop.prototype.next = function() {
>   77      var i = this.index0+1;
    78
    79      this.index0 = i;
    80      this.index = i+1;
    81
```
After:

```
    76      this.index0 = -1;
    77  }
    78
    79  ForLoop.prototype.next = function () {
>   80      var i = this.index0 + 1;
    81
    82      this.index0 = i;
    83      this.index = i + 1;
    84
```

Diff near the line:

```diff
@@ -73,17 +76,17 @@ export function ForLoop(parent, seq) {
     this.index0 = -1;
 }

-ForLoop.prototype.next = function() {
-    var i = this.index0+1;
+ForLoop.prototype.next = function () {
+    var i = this.index0 + 1;

     this.index0 = i;
-    this.index = i+1;
+    this.index = i + 1;

-    this.first = (i === 0);
-    this.last = (i === this.length-1);
+    this.first = i === 0;
+    this.last = i === this.length - 1;

-    this.odd = (this.index % 2 === 1);
-    this.even = (this.index % 2 === 0);
+    this.odd = this.index % 2 === 1;
+    this.even = this.index % 2 === 0;
     this.parity = ['even', 'odd'][this.index % 2];

     this.revindex0 = this.length - i;
```

## 6. hoppscotch: `CG-QUAL-101` (edited)

- Commit: [863b1b29a8](https://github.com/hoppscotch/hoppscotch/commit/863b1b29a803f6c456b04dd82d19a53c7afc9102), file `packages/hoppscotch-common/src/lib/sync/settings/index.ts` (was `packages/hoppscotch-selfhost-web/src/platform/settings/web/index.ts`)
- Truth: **known (edited)**, old line 49, new line 42
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    45    const res = await getUserSettings()
    46
    47    // create user settings if it doesn't exist
    48    E.isLeft(res) &&
>   49      res.left.error == "user_settings/not_found" &&
    50      (await createUserSettings(JSON.stringify(getDefaultSettings())))
    51
    52    if (E.isRight(res)) {
    53      runDispatchWithOutSyncing(() => {
```
After:

```
    38  async function loadUserSettings() {
    39    const res = await getUserSettings()
    40
    41    // create user settings if it doesn't exist
>   42    if (E.isLeft(res) && res.left.error == "user_settings/not_found") {
    43      const createRes = await createUserSettings(
    44        JSON.stringify(getDefaultSettings())
    45      )
    46
```

Diff near the line:

```diff
@@ -45,11 +39,19 @@ async function loadUserSettings() {
   const res = await getUserSettings()

   // create user settings if it doesn't exist
-  E.isLeft(res) &&
-    res.left.error == "user_settings/not_found" &&
-    (await createUserSettings(JSON.stringify(getDefaultSettings())))
+  if (E.isLeft(res) && res.left.error == "user_settings/not_found") {
+    const createRes = await createUserSettings(
+      JSON.stringify(getDefaultSettings())
+    )

-  if (E.isRight(res)) {
+    if (E.isRight(createRes)) {
+      runDispatchWithOutSyncing(() => {
+        bulkApplySettings(
+          JSON.parse(createRes.right.createUserSettings.properties)
+        )
+      })
+    }
+  } else if (E.isRight(res)) {
     runDispatchWithOutSyncing(() => {
       bulkApplySettings(JSON.parse(res.right.me.settings.properties))
     })

```

## 7. habitica: `CG-QUAL-103` (edited)

- Commit: [e6ffd69148](https://github.com/HabitRPG/habitica/commit/e6ffd69148396eeff7130b102a93d774fa11dcbc), file `website/common/script/ops/buy/purchase.js`
- Truth: **known (edited)**, old line 79, new line 79
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    75  }
    76
    77  const acceptedTypes = ['eggs', 'hatchingPotions', 'food', 'gear', 'bundles'];
    78  const singlePurchaseTypes = ['gear'];
>   79  export default async function purchase (user, req = {}, analytics) {
    80    const type = get(req.params, 'type');
    81    const key = get(req.params, 'key');
    82
    83    const quantity = req.quantity ? Number(req.quantity) : 1;
```
After:

```
    75  }
    76
    77  const acceptedTypes = ['eggs', 'hatchingPotions', 'food', 'gear', 'bundles'];
    78  const singlePurchaseTypes = ['gear'];
>   79  export default async function purchase (user, req = {}) {
    80    const type = get(req.params, 'type');
    81    const key = get(req.params, 'key');
    82
    83    const quantity = req.quantity ? Number(req.quantity) : 1;
```

Diff near the line:

```diff
@@ -76,7 +76,7 @@ async function purchaseItem (user, item, price, type, key) {

 const acceptedTypes = ['eggs', 'hatchingPotions', 'food', 'gear', 'bundles'];
 const singlePurchaseTypes = ['gear'];
-export default async function purchase (user, req = {}, analytics) {
+export default async function purchase (user, req = {}) {
   const type = get(req.params, 'type');
   const key = get(req.params, 'key');

```

## 8. habitica: `CG-QUAL-103` (edited)

- Commit: [e6ffd69148](https://github.com/HabitRPG/habitica/commit/e6ffd69148396eeff7130b102a93d774fa11dcbc), file `website/common/script/ops/feed.js`
- Truth: **known (edited)**, old line 39, new line 37
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    35      egg: pet.text(req.language),
    36    }, req.language);
    37  }
    38
>   39  export default function feed (user, req = {}, analytics) {
    40    let pet = get(req, 'params.pet');
    41    const foodK = get(req, 'params.food');
    42    let amount = Number(get(req.query, 'amount', 1));
    43    let foodFactor;
```
After:

```
    33      egg: pet.text(req.language),
    34    }, req.language);
    35  }
    36
>   37  export default function feed (user, req = {}) {
    38    let pet = get(req, 'params.pet');
    39    const foodK = get(req, 'params.food');
    40    let amount = Number(get(req.query, 'amount', 1));
    41    let foodFactor;
```

Diff near the line:

```diff
@@ -36,7 +34,7 @@ function evolve (user, pet, req) {
   }, req.language);
 }

-export default function feed (user, req = {}, analytics) {
+export default function feed (user, req = {}) {
   let pet = get(req, 'params.pet');
   const foodK = get(req, 'params.food');
   let amount = Number(get(req.query, 'amount', 1));
```

## 9. habitica: `CG-QUAL-103` (edited)

- Commit: [e6ffd69148](https://github.com/HabitRPG/habitica/commit/e6ffd69148396eeff7130b102a93d774fa11dcbc), file `website/common/script/ops/buy/hourglassPurchase.js`
- Truth: **known (edited)**, old line 16, new line 15
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    12  import getItemInfo from '../../libs/getItemInfo';
    13  import { removeItemByPath } from '../pinnedGearUtils';
    14  import updateUserHourglasses from '../updateUserHourglasses';
    15
>   16  export default async function purchaseHourglass (user, req = {}, analytics, quantity = 1) {
    17    const key = get(req, 'params.key');
    18    if (!key) throw new BadRequest(errorMessage('missingKeyParam'));
    19
    20    const type = get(req, 'params.type');
```
After:

```
    11  import getItemInfo from '../../libs/getItemInfo';
    12  import { removeItemByPath } from '../pinnedGearUtils';
    13  import updateUserHourglasses from '../updateUserHourglasses';
    14
>   15  export default async function purchaseHourglass (user, req = {}, quantity = 1) {
    16    const key = get(req, 'params.key');
    17    if (!key) throw new BadRequest(errorMessage('missingKeyParam'));
    18
    19    const type = get(req, 'params.type');
```

Diff near the line:

```diff
@@ -13,7 +12,7 @@ import getItemInfo from '../../libs/getItemInfo';
 import { removeItemByPath } from '../pinnedGearUtils';
 import updateUserHourglasses from '../updateUserHourglasses';

-export default async function purchaseHourglass (user, req = {}, analytics, quantity = 1) {
+export default async function purchaseHourglass (user, req = {}, quantity = 1) {
   const key = get(req, 'params.key');
   if (!key) throw new BadRequest(errorMessage('missingKeyParam'));

```

## 10. hedgedoc: `CG-SEC-103` (edited)

- Commit: [2eeb2c72c6](https://github.com/hedgedoc/hedgedoc/commit/2eeb2c72c680f2ce27b22a2d2e43fc86771a02f5), file `frontend/src/components/render-page/hooks/use-on-html-export-request.ts`
- Truth: **known (edited)**, old line 32, new line 41
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    28            if (!documentContainer) {
    29              return
    30            }
    31            const downloadElement = document.createElement('div')
>   32            downloadElement.innerHTML = documentContainer.innerHTML
    33            ;[
    34              ...downloadElement.querySelectorAll(`.${clickShieldCss['click-shield']}`),
    35              ...downloadElement.querySelectorAll(`.${copyButtonCss['copy-button']}`),
    36              ...downloadElement.querySelectorAll(`.${highlightedCodeCss['linenumber']}`)
```
After:

```
    37            if (!documentContainer) {
    38              return
    39            }
    40            const exportMarkdownBodyElement = document.createElement('div')
>   41            exportMarkdownBodyElement.innerHTML = documentContainer.innerHTML
    42            cleanupHtmlForExport(exportMarkdownBodyElement, noteUrl)
    43
    44            if (withStyles) {
    45              await extractImagesToBase64(exportMarkdownBodyElement)
```

Diff near the line:

```diff
@@ -23,27 +30,25 @@ export const useOnHtmlExportRequest = (communicator: RendererToEditorCommunicato
     CommunicationMessageType.EXPORT_HTML_REQUEST,
     useMemo(
       () =>
-        ({ noteUrl }) => {
-          const documentContainer = document.querySelector('.markdown-body')
+        async ({ noteUrl, withStyles, noteTitle }) => {
+          let finalHtml: string
+          const rootElementQuery = withStyles ? `.${markdownDocumentCss.document}` : '.markdown-body'
+          const documentContainer = document.querySelector(rootElementQuery)
           if (!documentContainer) {
             return
           }
-          const downloadElement = document.createElement('div')
-          downloadElement.innerHTML = documentContainer.innerHTML
-          ;[
-            ...downloadElement.querySelectorAll(`.${clickShieldCss['click-shield']}`),
-            ...downloadElement.querySelectorAll(`.${copyButtonCss['copy-button']}`),
-            ...downloadElement.querySelectorAll(`.${highlightedCodeCss['linenumber']}`)
-          ].forEach((element) => element.remove())
-          console.debug('Note URL to replace: ', noteUrl)
-          downloadElement.querySelectorAll('a[href]').forEach((element) => {
-            const href = element.getAttribute('href')
-            if (!href || !href.startsWith(noteUrl)) {
-              return
-            }
-            element.setAttribute('href', href.replace(noteUrl, ''))
-          })
-          const finalHtml = downloadElement.innerHTML
+          const exportMarkdownBodyElement = document.createElement('div')
+          exportMarkdownBodyElement.innerHTML = documentContainer.innerHTML
+          cleanupHtmlForExport(exportMarkdownBodyElement, noteUrl)
+
+          if (withStyles) {
+            await extractImagesToBase64(exportMarkdownBodyElement)
+            const finalHtmlElement = await buildFullHtmlPageForExport(exportMarkdownBodyElement, noteTitle)
+            finalHtml = finalHtmlElement.outerHTML
+          } else {
+            finalHtml = exportMarkdownBodyElement.innerHTML
+          }
... (4 more lines)
```

## 11. ghost: `CG-PERF-101` (edited)

- Commit: [0f623f3f5d](https://github.com/TryGhost/Ghost/commit/0f623f3f5daf914e9896e29cfe28bfbce0f0a8e3), file `tools/scripts/check-internal-packages.ts`
- Truth: **known (edited)**, old line 285, new line 339
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
   281          conditions.default,
   282          `./build/${sourceStem}.js`,
   283          `exports.${entryPoint}.default`,
   284        );
>  285        if (!(await exists(path.join(packageDirectory, conditions.source)))) {
   286          errors.push(
   287            `${manifestPath}: exports.${entryPoint}.source does not exist (${conditions.source})`,
   288          );
   289        }
```
After:

```
   335          conditions.default,
   336          `./build/${sourceStem}.js`,
   337          `exports.${entryPoint}.default`,
   338        );
>  339        if (!(await exists(path.join(packageDirectory, conditions.source as string)))) {
   340          errors.push(
   341            `${manifestPath}: exports.${entryPoint}.source does not exist (${conditions.source as string})`,
   342          );
   343        }
```

Diff near the line:

```diff
@@ -282,14 +336,14 @@ async function validateCompliantPackage({
         `./build/${sourceStem}.js`,
         `exports.${entryPoint}.default`,
       );
-      if (!(await exists(path.join(packageDirectory, conditions.source)))) {
+      if (!(await exists(path.join(packageDirectory, conditions.source as string)))) {
         errors.push(
-          `${manifestPath}: exports.${entryPoint}.source does not exist (${conditions.source})`,
+          `${manifestPath}: exports.${entryPoint}.source does not exist (${conditions.source as string})`,
         );
       }
     }

-    const rootExport = exports['.'];
+    const rootExport = (exports as JsonObject)['.'] as JsonObject | undefined;
     if (!rootExport) {
       errors.push(`${manifestPath}: exports must define the "." entry point`);
     } else {
```

## 12. kiwi: `CG-SEC-109` (edited)

- Commit: [362febe930](https://github.com/kiwitcms/Kiwi/commit/362febe93063899b8c7468cf7490c26028368a5c), file `tcms/testplans/static/testplans/js/clone.js`
- Truth: **known (edited)**, old line 110, new line 112
- Schemes that disagree with the truth: `github` (false_new), `line_text` (false_new)

Before:

```
   106
   107              if (newPlanIds.length === 1) {
   108                  window.location.assign(`/plan/${newPlanIds[0]}/`)
   109              } else {
>  110                  window.location.assign(document.referrer || '/')
   111              }
   112          }
   113
   114          if (!rows.length) {
```
After:

```
   108              const redirectToClonedPlan = function () {
   109                  if (isTree || newPlanIds.length === 1) {
   110                      window.location.assign(`/plan/${newPlanIds[0]}/`)
   111                  } else {
>  112                      window.location.assign(document.referrer || '/')
   113                  }
   114              }
   115
   116              // in tree mode set the parent of every clone, which can only be
```

Diff near the line:

```diff
@@ -104,11 +105,44 @@ export function pageTestplansCloneReadyHandler () {
                 return
             }

-            if (newPlanIds.length === 1) {
-                window.location.assign(`/plan/${newPlanIds[0]}/`)
-            } else {
-                window.location.assign(document.referrer || '/')
+            const redirectToClonedPlan = function () {
+                if (isTree || newPlanIds.length === 1) {
+                    window.location.assign(`/plan/${newPlanIds[0]}/`)
+                } else {
+                    window.location.assign(document.referrer || '/')
+                }
             }
+
+            // in tree mode set the parent of every clone, which can only be
+            // done once all of the clones have been created.
+            if (isTree) {
+                let updatedCount = 0
+
+                const updateIsDone = function () {
+                    updatedCount += 1
+
+                    if (updatedCount === rows.length) {
+                        redirectToClonedPlan()
+                    }
+                }
+
+                rows.each(function () {
+                    const row = $(this)
+
+                    jsonRPC(
+                        'TestPlan.update',
+                        [
+                            clonedPlanIds[row.data('plan-id')],
+                            { parent: clonedPlanIds[row.attr('data-parent-id')] }
+                        ],
+                        updateIsDone
+                    )
... (10 more lines)
```

## 13. hoppscotch: `CG-PERF-101` (edited)

- Commit: [9861ee84ad](https://github.com/hoppscotch/hoppscotch/commit/9861ee84ad593372885ebfc7cb1c487f3b9dd290), file `packages/hoppscotch-desktop/src/services/persistence.service.ts`
- Truth: **known (edited)**, old line 112, new line 294
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
   108
   109      if (currentVersion !== targetVersion) {
   110        for (const migration of migrations) {
   111          if (migration.version > parseInt(currentVersion)) {
>  112            await migration.migrate()
   113          }
   114        }
   115
   116        await Store.set(STORE_NAMESPACE, STORE_KEYS.SCHEMA_VERSION, targetVersion)
```
After:

```
   290      }
   291
   292      for (const migration of migrations) {
   293        if (migration.version > parseInt(currentVersion, 10)) {
>  294          const result = await migration.migrate()
   295          if (E.isLeft(result)) {
   296            return result
   297          }
   298        }
```

Diff near the line:

```diff
@@ -87,176 +216,150 @@ export class DesktopPersistenceService {
   async init(): Promise<E.Either<StoreError, void>> {
     const initResult = await Store.init()
     if (E.isLeft(initResult)) {
-      console.error(
-        "[PersistenceService] Failed to initialize store:",
-        initResult.left
-      )
+      Log.error(LOG_TAG, "Failed to initialize store", initResult.left)
       return initResult
     }
-    await this.runMigrations()
-    return initResult
-  }
-
-  private async runMigrations() {
-    const versionResult = await Store.get<string>(
-      STORE_NAMESPACE,
-      STORE_KEYS.SCHEMA_VERSION
-    )
-    const perhapsVersion = E.isRight(versionResult) ? versionResult.right : "1"
-    const currentVersion = perhapsVersion ?? "1"
-    const targetVersion = "1"
-
-    if (currentVersion !== targetVersion) {
-      for (const migration of migrations) {
-        if (migration.version > parseInt(currentVersion)) {
-          await migration.migrate()
-        }
-      }
-
-      await Store.set(STORE_NAMESPACE, STORE_KEYS.SCHEMA_VERSION, targetVersion)
+    const migrationResult = await this.runMigrations()
+    if (E.isLeft(migrationResult)) {
+      return migrationResult
     }
+    await this.setupRustSync()
+    return E.right(undefined)
   }

... (259 more lines)
```

## 14. uptime-kuma: `CG-SEC-105` (edited)

- Commit: [4e7c4ae382](https://github.com/louislam/uptime-kuma/commit/4e7c4ae382f4038369922a7981babba43403ff1c), file `test/backend-test/test-migration-v2-to-v3.ts`
- Truth: **known (edited)**, old line 17, new line 21
- Schemes that disagree with the truth: `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    13  const fixturePath = path.join(__dirname, "../fixtures/v2-kuma.db.gz");
    14  const dataDir = path.join(__dirname, "../../data/test-migration-v2-upgrade");
    15
    16  const username = "admin";
>   17  const password = "Kuma-V2-Test-Password";
    18
    19  /**
    20   * Get a free TCP port from the OS.
    21   * @returns {Promise<number>} A free port
```
After:

```
    17
    18  const username = "admin";
    19
    20  // A password that Have I Been Pwned reports as breached, to cover the migration path from #7946.
>   21  const password = "Admin123!x";
    22
    23  /**
    24   * Get a free TCP port from the OS.
    25   * @returns {Promise<number>} A free port
```

Diff near the line:

```diff
@@ -7,6 +7,8 @@ import zlib from "node:zlib";
 import { spawn } from "node:child_process";
 import { fileURLToPath } from "node:url";
 import { io } from "socket.io-client";
+import BetterSqlite3 from "better-sqlite3";
+import bcrypt from "bcryptjs";

 const __dirname = path.dirname(fileURLToPath(import.meta.url));

@@ -14,7 +16,9 @@ const fixturePath = path.join(__dirname, "../fixtures/v2-kuma.db.gz");
 const dataDir = path.join(__dirname, "../../data/test-migration-v2-upgrade");

 const username = "admin";
-const password = "Kuma-V2-Test-Password";
+
+// A password that Have I Been Pwned reports as breached, to cover the migration path from #7946.
+const password = "Admin123!x";

 /**
  * Get a free TCP port from the OS.
```

## 15. calcom: `CG-QUAL-103` (edited)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/payment/handleNoShowFee.ts`
- Truth: **known (edited)**, old line 21, new line 19
- Schemes that disagree with the truth: `line_text` (false_new)

Before:

```
    17  import type { Prisma } from "@calcom/prisma/client";
    18  import type { CalendarEvent } from "@calcom/types/Calendar";
    19  import type { IAbstractPaymentService } from "@calcom/types/PaymentService";
    20
>   21  export const handleNoShowFee = async ({
    22    booking,
    23    payment,
    24  }: {
    25    booking: {
```
After:

```
    15  import type { Prisma } from "@calcom/prisma/client";
    16  import type { CalendarEvent } from "@calcom/types/Calendar";
    17  import type { IAbstractPaymentService } from "@calcom/types/PaymentService";
    18
>   19  export const handleNoShowFee= async ({
    20    booking,
    21    payment,
    22  }: {
    23    booking: {
```

Diff near the line:

```diff
@@ -3,12 +3,10 @@ import { eventTypeMetaDataSchemaWithTypedApps } from "@calcom/app-store/zod-util
 import dayjs from "@calcom/dayjs";
 import { sendNoShowFeeChargedEmail } from "@calcom/emails/billing-email-service";
 import { CredentialRepository } from "@calcom/features/credentials/repositories/CredentialRepository";
-import { TeamRepository } from "@calcom/features/ee/teams/repositories/TeamRepository";
 import {
   type EventTypeBrandingData,
   getEventTypeService,
 } from "@calcom/features/eventtypes/di/EventTypeService.container";
-import { MembershipRepository } from "@calcom/features/membership/repositories/MembershipRepository";
 import { ErrorCode } from "@calcom/lib/errorCodes";
 import { ErrorWithCode } from "@calcom/lib/errors";
 import logger from "@calcom/lib/logger";
@@ -18,7 +16,7 @@ import type { Prisma } from "@calcom/prisma/client";
 import type { CalendarEvent } from "@calcom/types/Calendar";
 import type { IAbstractPaymentService } from "@calcom/types/PaymentService";

-export const handleNoShowFee = async ({
+export const handleNoShowFee= async ({
   booking,
   payment,
 }: {
```

## 16. hedgedoc: `CG-PERF-101` (edited)

- Commit: [c2ccf48c39](https://github.com/hedgedoc/hedgedoc/commit/c2ccf48c3966608f7292c6818d1b95469aa1b3cd), file `backend/src/api/public/notes/notes.controller.ts`
- Truth: **known (edited)**, old line 134, new line 134
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new)

Before:

```
   130      for (const mediaUpload of mediaUploads) {
   131        if (!noteMediaDeletionDto.keepMedia) {
   132          await this.mediaService.deleteFile(mediaUpload);
   133        } else {
>  134          await this.mediaService.removeNoteFromMediaUpload(mediaUpload);
   135        }
   136      }
   137      this.logger.debug(`Deleting note: ${noteId}`, 'deleteNote');
   138      await this.noteService.deleteNote(noteId);
```
After:

```
   130      for (const mediaUpload of mediaUploads) {
   131        if (!noteMediaDeletionDto.keepMedia) {
   132          await this.mediaService.deleteFile(mediaUpload);
   133        } else {
>  134          await this.mediaService.removeNoteFromMediaUpload(mediaUpload, noteId);
   135        }
   136      }
   137      this.logger.debug(`Deleting note: ${noteId}`, 'deleteNote');
   138      await this.noteService.deleteNote(noteId);
```

Diff near the line:

```diff
@@ -131,7 +131,7 @@ export class NotesController {
       if (!noteMediaDeletionDto.keepMedia) {
         await this.mediaService.deleteFile(mediaUpload);
       } else {
-        await this.mediaService.removeNoteFromMediaUpload(mediaUpload);
+        await this.mediaService.removeNoteFromMediaUpload(mediaUpload, noteId);
       }
     }
     this.logger.debug(`Deleting note: ${noteId}`, 'deleteNote');

```

## 17. warehouse: `CG-SEC-103` (edited)

- Commit: [7320d9052b](https://github.com/pypi/warehouse/commit/7320d9052b59a7e3b1c2122034396f5d339cd3e0), file `tests/frontend/filter_list_controller_test.js`
- Truth: **known (edited)**, old line 39, new line 101
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
    35    describe("is initialized as expected", () => {
    36      describe("makes expected elements visible", () => {
    37        let application;
    38        beforeEach(() => {
>   39          document.body.innerHTML = `
    40        <div id="controller" data-controller="filter-list">
    41          ${testFixtureHTMLVisibilityToggle}
    42        </div>
    43        `;
```
After:

```
    97      expect(Array.from(filterMyAttr.options).map(option => [option.value, option.selected])).toEqual(values);
    98    };
    99    const appStart = async function () {
   100      const div = document.createElement("div");
>  101      div.innerHTML = `
   102        <div id="controller" data-controller="filter-list">
   103          ${testFixtureHTMLVisibilityToggle}
   104          ${testFixtureHTMLShowing}
   105          ${testFixtureHTMLFilters}
```

Diff near the line:

```diff
@@ -5,226 +5,424 @@

 import {Application} from "@hotwired/stimulus";
 import FilterListController from "../../warehouse/static/js/warehouse/controllers/filter_list_controller";
+import {delay} from "./utils";


 const testFixtureHTMLVisibilityToggle = `
-<p id="initial-toggle-visibility-shown" class="hidden initial-toggle-visibility">Initially hidden, should end up shown.</p>
-<p id="initial-toggle-visibility-hidden" class="initial-toggle-visibility">Initially shown, should end up hidden.</p>
+<p id="initial-toggle-visibility-shown" class="hidden initial-toggle-visibility">
+    Initially hidden, should end up shown.
+</p>
+<p id="initial-toggle-visibility-hidden" class="initial-toggle-visibility">
+    Initially shown, should end up hidden.
+</p>
 `;
 const testFixtureHTMLShowing = `
 <p id="shown-and-total" data-filter-list-target="summary"></p>
 `;
 const testFixtureHTMLFilters = `
-<input id="filter-input" type="text" data-action="filter-list#filter" data-filter-list-target="filter" data-filtered-source="contentType">
-        <select id="filter-select"  data-action="filter-list#filter" data-filter-list-target="filter" data-filtered-source="myattr">
-          <option selected value="">My Attrs</option>
-          <option value="myattr1">myattr 1</option>
-          <option value="myattr2">myattr 2</option>
-          <option value="myattr3">myattr 3</option>
-        </select>
+<input id="filter-input-description" type="text" data-action="filter-list#filter"
+    data-filter-list-target="filter" data-filtered-source="description" data-comparison-type="includes"
+    data-auto-update-url-querystring="false">
+<select id="filter-select-myattr" data-action="filter-list#filter"
+    data-filter-list-target="filter" data-filtered-source="myattr" data-comparison-type="exact"
+    data-auto-update-url-querystring="true">
+  <option value="" selected>My Attrs</option>
+  <option value="myattr1">myattr 1</option>
+  <option value="myattr2">myattr 2</option>
+  <option value="myattr3">myattr 3</option>
+</select>
+<select id="filter-select-contentType" data-action="filter-list#filter"
... (557 more lines)
```

## 18. pgadmin: `CG-QUAL-101` (edited)

- Commit: [5f56805162](https://github.com/pgadmin-org/pgadmin4/commit/5f56805162c117ac1de17368ef8fdc0b07221e2c), file `web/pgadmin/tools/sqleditor/static/js/components/QueryToolComponent.jsx`
- Truth: **known (edited)**, old line 813, new line 872
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
   809            let existIdx = _.findIndex(qtState.connection_list, (conn)=>{
   810              conn.role= conn.role == ''? null :conn.role;
   811              return(
   812                conn.sid == connectionData.sid  && conn.database_name == connectionData.database_name
>  813                && conn.user == connectionData.user && conn.role == connectionData.role
   814              );
   815            });
   816            if(existIdx > -1) {
   817              reject(new Error(gettext('Connection with this configuration already present.')));
```
After:

```
   868
   869            let existIdx = _.findIndex(qtState.connection_list, (conn)=>{
   870              return(
   871                conn.sid == connectionData.sid  && conn.database_name == connectionData.database_name
>  872                && conn.user == connectionData.user && (conn.role || null) == (connectionData.role || null)
   873              );
   874            });
   875            if(existIdx > -1) {
   876              reject(new Error(gettext('Connection with this configuration already present.')));
```

Diff near the line:

```diff
@@ -807,10 +867,9 @@ export default function QueryToolComponent({params, pgWindow, pgAdmin, selectedN
           };

           let existIdx = _.findIndex(qtState.connection_list, (conn)=>{
-            conn.role= conn.role == ''? null :conn.role;
             return(
               conn.sid == connectionData.sid  && conn.database_name == connectionData.database_name
-              && conn.user == connectionData.user && conn.role == connectionData.role
+              && conn.user == connectionData.user && (conn.role || null) == (connectionData.role || null)
             );
           });
           if(existIdx > -1) {
@@ -818,11 +877,12 @@ export default function QueryToolComponent({params, pgWindow, pgAdmin, selectedN
             return;
           }
           updateQueryToolConnection(connectionData, true)
-            .catch((err)=>{
-              reject(err instanceof Error ? err : Error(gettext('Something went wrong')));
-            }).then(()=>{
+            .then(()=>{
               resolve();
               onClose();
+            })
+            .catch((err)=>{
+              reject(err instanceof Error ? err : Error(gettext('Something went wrong')));
             });
         });
       }}
```

## 19. indico: `CG-QUAL-003` (edited)

- Commit: [4c706171e6](https://github.com/indico/indico/commit/4c706171e684907abb2a5a032d81be1c10f919b0), file `indico/modules/events/registration/util.py`
- Truth: **known (edited)**, old line 596, new line 596
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new), `sonar` (false_new)

Before:

```
   592          for item in regform_items if item.input_type == 'date'
   593      }
   594
   595
>  596  def generate_spreadsheet_from_registrations(registrations, regform_items, static_items):
   597      """Generate a spreadsheet data from a given registration list.
   598
   599      :param registrations: The list of registrations to include in the file
   600      :param regform_items: The registration form items to be used as columns
```
After:

```
   592          for item in regform_items if item.input_type == 'date'
   593      }
   594
   595
>  596  def generate_spreadsheet_from_registrations(registrations, regform_items, static_items, extra_columns=()):
   597      """Generate a spreadsheet data from a given registration list.
   598
   599      :param registrations: The list of registrations to include in the file
   600      :param regform_items: The registration form items to be used as columns
```

Diff near the line:

```diff
@@ -593,12 +593,13 @@ def get_registration_spreadsheet_column_formats(regform_items):
     }


-def generate_spreadsheet_from_registrations(registrations, regform_items, static_items):
+def generate_spreadsheet_from_registrations(registrations, regform_items, static_items, extra_columns=()):
     """Generate a spreadsheet data from a given registration list.

     :param registrations: The list of registrations to include in the file
     :param regform_items: The registration form items to be used as columns
     :param static_items: Registration form information as extra columns
+    :param extra_columns: Custom list items from the `registrant_list_items` signal
     """
     field_names = ['ID', 'Name']
     special_item_mapping = {
```

## 20. edx-platform: `CG-SEC-013` (edited)

- Commit: [b3f862e61a](https://github.com/openedx/edx-platform/commit/b3f862e61aa84a5f8c027081b7d1a07a8619917d), file `cms/djangoapps/contentstore/api/views/course_import.py`
- Truth: **known (edited)**, old line 142, new line 145
- Schemes that disagree with the truth: `line_text` (false_new)

Before:

```
   138              if not course_dir.isdir():
   139                  os.mkdir(course_dir)
   140
   141              log.debug(f'importing course to {temp_filepath}')
>  142              with open(temp_filepath, "wb+") as temp_file:
   143                  for chunk in request.FILES['course_data'].chunks():
   144                      temp_file.write(chunk)
   145
   146              log.info("Course import %s: Upload complete", course_key)
```
After:

```
   141              os.makedirs(course_dir, exist_ok=True)
   142
   143              try:
   144                  log.debug(f'importing course to {temp_filepath}')
>  145                  with open(temp_filepath, "wb+") as temp_file:
   146                      for chunk in request.FILES['course_data'].chunks():
   147                          temp_file.write(chunk)
   148
   149                  log.info("Course import %s: Upload complete", course_key)
```

Diff near the line:

```diff
@@ -131,22 +134,26 @@ class CourseImportView(CourseImportExportViewMixin, GenericAPIView):
                     developer_message='Parameter in the wrong format',
                     error_code='internal_error',
                 )
-            course_dir = path(settings.GITHUB_REPO_ROOT) / base64.urlsafe_b64encode(
-                repr(course_key).encode('utf-8')
-            ).decode('utf-8')
+            # Staging directory private to this upload, so that a concurrent import of
+            # the same course cannot overwrite this archive or delete it on its way out.
+            course_dir = course_import_working_dir(course_key, f'upload-{uuid4().hex}')
             temp_filepath = course_dir / filename
-            if not course_dir.isdir():
-                os.mkdir(course_dir)
-
-            log.debug(f'importing course to {temp_filepath}')
-            with open(temp_filepath, "wb+") as temp_file:
-                for chunk in request.FILES['course_data'].chunks():
-                    temp_file.write(chunk)
-
-            log.info("Course import %s: Upload complete", course_key)
-            with open(temp_filepath, 'rb') as local_file:
-                django_file = File(local_file)
-                storage_path = course_import_export_storage.save('olx_import/' + filename, django_file)
+            os.makedirs(course_dir, exist_ok=True)
+
+            try:
+                log.debug(f'importing course to {temp_filepath}')
+                with open(temp_filepath, "wb+") as temp_file:
+                    for chunk in request.FILES['course_data'].chunks():
+                        temp_file.write(chunk)
+
+                log.info("Course import %s: Upload complete", course_key)
+                with open(temp_filepath, 'rb') as local_file:
+                    django_file = File(local_file)
+                    storage_path = course_import_export_storage.save('olx_import/' + filename, django_file)
+            finally:
+                # The archive now lives in storage; the import task downloads it into its
+                # own working directory, so this staging copy is no longer needed.
+                remove_course_import_working_dir(course_dir)

... (3 more lines)
```

## 21. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 1370, new line 1704
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (mispaired)

Before:

```
  1366                    {
  1367                      type: appStoreMetadata.dailyvideo.type,
  1368                      uid: "MOCK_ID",
  1369                      meetingId: "MOCK_ID",
> 1370                      meetingPassword: "MOCK_PASS",
  1371                      meetingUrl: "http://mock-dailyvideo.example.com",
  1372                    },
  1373                    {
  1374                      type: appStoreMetadata.googlecalendar.type,
```
After:

```
  1700                    {
  1701                      type: appStoreMetadata.dailyvideo.type,
  1702                      uid: "MOCK_ID",
  1703                      meetingId: "MOCK_ID",
> 1704                      meetingPassword: "MOCK_PASS",
  1705                      meetingUrl: "http://mock-dailyvideo.example.com",
  1706                    },
  1707                    {
  1708                      type: appStoreMetadata.googlecalendar.type,
```

## 22. documenso: `CG-SEC-105` (known_but_new)

- Commit: [97835b8dbb](https://github.com/documenso/documenso/commit/97835b8dbb2ca24670c8a410972d949c982c8f61), file `packages/app-tests/e2e/envelope-editor-v2/envelope-fields.spec.ts`
- Truth: **known (equal)**, old line 1000, new line 1149
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
   996    test('place and configure all 10 field types', async ({ page }) => {
   997      const surface = await openEmbeddedEnvelopeEditor(page, {
   998        envelopeType: 'TEMPLATE',
   999        mode: 'edit',
> 1000        tokenNamePrefix: 'e2e-embed-all-fields',
  1001      });
  1002      const result = await runAllFieldTypesFlow(surface);
  1003
  1004      await persistEmbeddedEnvelope(surface);
```
After:

```
  1145    test('place and configure all 10 field types', async ({ page }) => {
  1146      const surface = await openEmbeddedEnvelopeEditor(page, {
  1147        envelopeType: 'TEMPLATE',
  1148        mode: 'edit',
> 1149        tokenNamePrefix: 'e2e-embed-all-fields',
  1150      });
  1151      const result = await runAllFieldTypesFlow(surface);
  1152
  1153      await persistEmbeddedEnvelope(surface);
```

## 23. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 2486, new line 3172
- Schemes that disagree with the truth: `codeguard` (false_new), `line_text` (false_new)

Before:

```
  2482                    {
  2483                      type: appStoreMetadata.dailyvideo.type,
  2484                      uid: "MOCK_ID",
  2485                      meetingId: "MOCK_ID",
> 2486                      meetingPassword: "MOCK_PASS",
  2487                      meetingUrl: "http://mock-dailyvideo.example.com",
  2488                      credentialId: null,
  2489                    },
  2490                    {
```
After:

```
  3168                    {
  3169                      type: appStoreMetadata.dailyvideo.type,
  3170                      uid: "MOCK_ID",
  3171                      meetingId: "MOCK_ID",
> 3172                      meetingPassword: "MOCK_PASS",
  3173                      meetingUrl: "http://mock-dailyvideo.example.com",
  3174                      credentialId: null,
  3175                    },
  3176                    {
```

## 24. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 1260, new line 1594
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new)

Before:

```
  1256                        {
  1257                          type: appStoreMetadata.dailyvideo.type,
  1258                          uid: "MOCK_ID",
  1259                          meetingId: "MOCK_ID",
> 1260                          meetingPassword: "MOCK_PASS",
  1261                          meetingUrl: "http://mock-dailyvideo.example.com",
  1262                        },
  1263                        {
  1264                          type: appStoreMetadata.googlecalendar.type,
```
After:

```
  1590                        {
  1591                          type: appStoreMetadata.dailyvideo.type,
  1592                          uid: "MOCK_ID",
  1593                          meetingId: "MOCK_ID",
> 1594                          meetingPassword: "MOCK_PASS",
  1595                          meetingUrl: "http://mock-dailyvideo.example.com",
  1596                        },
  1597                        {
  1598                          type: appStoreMetadata.googlecalendar.type,
```

## 25. openlibrary: `CG-SEC-001` (known_but_new)

- Commit: [f5aff19fb7](https://github.com/internetarchive/openlibrary/commit/f5aff19fb7d0c27f3bb91f08db81a8750bae604a), file `openlibrary/tests/core/test_bookshelves_events_async.py`
- Truth: **known (equal)**, old line 48, new line 136
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
    44                      "VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    45                      {"u": "alice", "w": work_id, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-05-01"},
    46                  )
    47              # Duplicate on 101 stays distinct. START and 2025 rows must not count.
>   48              await conn.execute(
    49                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    50                  {"u": "alice", "w": 101, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-06-01"},
    51              )
    52              await conn.execute(
```
After:

```
   132                      "VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   133                      {"u": "alice", "w": work_id, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-05-01"},
   134                  )
   135              # Duplicate on 101 stays distinct. START and 2025 rows must not count.
>  136              await conn.execute(
   137                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   138                  {"u": "alice", "w": 101, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-06-01"},
   139              )
   140              await conn.execute(
```

## 26. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 1395, new line 1728
- Schemes that disagree with the truth: `codeguard` (false_new), `line_text` (false_new)

Before:

```
  1391                bookingRef: {
  1392                  type: appStoreMetadata.dailyvideo.type,
  1393                  uid: "MOCK_ID",
  1394                  meetingId: "MOCK_ID",
> 1395                  meetingPassword: "MOCK_PASS",
  1396                  meetingUrl: "http://mock-dailyvideo.example.com",
  1397                },
  1398              });
  1399
```
After:

```
  1724                bookingRef: {
  1725                  type: appStoreMetadata.dailyvideo.type,
  1726                  uid: "MOCK_ID",
  1727                  meetingId: "MOCK_ID",
> 1728                  meetingPassword: "MOCK_PASS",
  1729                  meetingUrl: "http://mock-dailyvideo.example.com",
  1730                },
  1731              });
  1732
```

## 27. kitsune: `CG-QUAL-104` (known_but_new)

- Commit: [59b6937db5](https://github.com/mozilla/kitsune/commit/59b6937db573505c764bec9c87bd786981848487), file `kitsune/sumo/static/sumo/js/markup.js`
- Truth: **known (equal)**, old line 965, new line 969
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
   961        });
   962      }
   963
   964      function loadCannedResponses() {
>  965        var siteLanguage = window.location.pathname.split("/")[1];
   966        var targetUrl = "/" + siteLanguage + cannedResponsesUrl;
   967
   968        apiFetch(targetUrl, { method: "GET", dataType: "html" })
   969          .then(function (responseHtml) {
```
After:

```
   965        });
   966      }
   967
   968      function loadCannedResponses() {
>  969        var siteLanguage = window.location.pathname.split("/")[1];
   970        var targetUrl = "/" + siteLanguage + cannedResponsesUrl;
   971
   972        apiFetch(targetUrl, { method: "GET", dataType: "html" })
   973          .then(function (responseHtml) {
```

## 28. erpnext: `CG-PERF-002` (known_but_new)

- Commit: [750bf9d9b3](https://github.com/frappe/erpnext/commit/750bf9d9b378fb92eab68733ae727214f3961c0a), file `erpnext/stock/utils.py`
- Truth: **known (equal)**, old line 159, new line 185
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
   155  						frappe.bold(field), frappe.bold("Inventory Dimension")
   156  					)
   157  				)
   158  			args[field] = value
>  159  			extra_cond += f" and {field} = %({field})s"
   160
   161  	last_entry = get_previous_sle(args, extra_cond=extra_cond)
   162
   163  	if with_valuation_rate:
```
After:

```
   181  						frappe.bold(field), frappe.bold("Inventory Dimension")
   182  					)
   183  				)
   184  			args[field] = value
>  185  			extra_cond += f" and {field} = %({field})s"
   186
   187  	last_entry = get_previous_sle(args, extra_cond=extra_cond)
   188
   189  	if with_valuation_rate:
```

## 29. openlibrary: `CG-SEC-001` (known_but_new)

- Commit: [f5aff19fb7](https://github.com/internetarchive/openlibrary/commit/f5aff19fb7d0c27f3bb91f08db81a8750bae604a), file `openlibrary/tests/core/test_bookshelves_events_async.py`
- Truth: **known (equal)**, old line 52, new line 140
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
    48              await conn.execute(
    49                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    50                  {"u": "alice", "w": 101, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-06-01"},
    51              )
>   52              await conn.execute(
    53                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    54                  {"u": "alice", "w": 104, "e": 1, "t": BookshelfEvent.START, "d": "2026-05-01"},
    55              )
    56              await conn.execute(
```
After:

```
   136              await conn.execute(
   137                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   138                  {"u": "alice", "w": 101, "e": 1, "t": BookshelfEvent.FINISH, "d": "2026-06-01"},
   139              )
>  140              await conn.execute(
   141                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   142                  {"u": "alice", "w": 104, "e": 1, "t": BookshelfEvent.START, "d": "2026-05-01"},
   143              )
   144              await conn.execute(
```

## 30. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 2622, new line 3308
- Schemes that disagree with the truth: `codeguard` (false_new), `line_text` (false_new)

Before:

```
  2618                    getMockBookingReference({
  2619                      type: "google_calendar",
  2620                      uid: "MOCK_ID",
  2621                      meetingId: "MOCK_ID",
> 2622                      meetingPassword: "MOCK_PASS",
  2623                      meetingUrl: "http://mock-google-meet.example.com",
  2624                      externalCalendarId: "MOCK_EXTERNAL_CALENDAR_ID",
  2625                      credentialId: 1,
  2626                    }),
```
After:

```
  3304                    getMockBookingReference({
  3305                      type: "google_calendar",
  3306                      uid: "MOCK_ID",
  3307                      meetingId: "MOCK_ID",
> 3308                      meetingPassword: "MOCK_PASS",
  3309                      meetingUrl: "http://mock-google-meet.example.com",
  3310                      externalCalendarId: "MOCK_EXTERNAL_CALENDAR_ID",
  3311                      credentialId: 1,
  3312                    }),
```

## 31. nodebb: `CG-SEC-105` (known_but_new)

- Commit: [9d122948cf](https://github.com/NodeBB/NodeBB/commit/9d122948cf783fc72c8c01c7aab0f42b2561b3c3), file `test/user.js`
- Truth: **known (equal)**, old line 2384, new line 2415
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
  2380  				const token = await db.get(`invitation:uid:${inviterUid}:invited:${email}`);
  2381
  2382  				const { body } = await helpers.registerUser({
  2383  					username: 'invite5',
> 2384  					password: '123456',
  2385  					'password-confirm': '123456',
  2386  					email: email,
  2387  					gdpr_consent: true,
  2388  					token: token,
```
After:

```
  2411  				const token = await db.get(`invitation:uid:${inviterUid}:invited:${email}`);
  2412
  2413  				const { body } = await helpers.registerUser({
  2414  					username: 'invite5',
> 2415  					password: '123456',
  2416  					'password-confirm': '123456',
  2417  					email: email,
  2418  					gdpr_consent: true,
  2419  					token: token,
```

## 32. lnbits: `CG-QUAL-102` (known_but_new)

- Commit: [f5989201d9](https://github.com/lnbits/lnbits/commit/f5989201d9c21a4690334f91bbbb421214c989e7), file `lnbits/static/js/wasm-extension-component.js`
- Truth: **known (equal)**, old line 904, new line 1126
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
   900        socket.addEventListener('message', event => {
   901          let data = event.data
   902          try {
   903            data = JSON.parse(event.data)
>  904          } catch (_error) {}
   905
   906          this.sendBridgeEvent({
   907            event: 'payment.update',
   908            subscriptionId,
```
After:

```
  1122        socket.addEventListener('message', event => {
  1123          let data = event.data
  1124          try {
  1125            data = JSON.parse(event.data)
> 1126          } catch (_error) {}
  1127
  1128          this.sendBridgeEvent({
  1129            event: 'payment.update',
  1130            subscriptionId,
```

## 33. erpnext: `CG-QUAL-101` (known_but_new)

- Commit: [ddc764b360](https://github.com/frappe/erpnext/commit/ddc764b3608610fa659dd722da44e115850cc4da), file `erpnext/stock/doctype/material_request/material_request.js`
- Truth: **known (equal)**, old line 810, new line 809
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
   806  				doc.material_request_type == "Purchase" ||
   807  				doc.material_request_type == "Subcontracting"
   808  			) {
   809  				filters = { is_purchase_item: 1 };
>  810  			} else if (doc.material_request_type == "Manufacture") {
   811  				filters.include_item_in_manufacturing = 1;
   812  			}
   813
   814  			return {
```
After:

```
   805  			} else if (doc.material_request_type == "Purchase") {
   806  				filters = { is_purchase_item: 1 };
   807  			} else if (doc.material_request_type == "Subcontracting") {
   808  				filters = { is_stock_item: 1, is_sub_contracted_item: 1 };
>  809  			} else if (doc.material_request_type == "Manufacture") {
   810  				filters.include_item_in_manufacturing = 1;
   811  			}
   812
   813  			return {
```

## 34. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 2494, new line 3180
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new)

Before:

```
  2490                    {
  2491                      type: appStoreMetadata.googlecalendar.type,
  2492                      uid: "MOCK_ID",
  2493                      meetingId: "MOCK_ID",
> 2494                      meetingPassword: "MOCK_PASSWORD",
  2495                      meetingUrl: "https://UNUSED_URL",
  2496                      externalCalendarId: "MOCK_EXTERNAL_CALENDAR_ID",
  2497                      credentialId: undefined,
  2498                    },
```
After:

```
  3176                    {
  3177                      type: appStoreMetadata.googlecalendar.type,
  3178                      uid: "MOCK_ID",
  3179                      meetingId: "MOCK_ID",
> 3180                      meetingPassword: "MOCK_PASSWORD",
  3181                      meetingUrl: "https://UNUSED_URL",
  3182                      externalCalendarId: "MOCK_EXTERNAL_CALENDAR_ID",
  3183                      credentialId: undefined,
  3184                    },
```

## 35. arches: `CG-QUAL-104` (known_but_new)

- Commit: [2e02ce6e61](https://github.com/archesproject/arches/commit/2e02ce6e61999d93c10b05d853ae08f1912fa294), file `arches/app/media/js/views/graph/permission-manager/permission-settings-form.js`
- Truth: **known (equal)**, old line 128, new line 210
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new)

Before:

```
   124          });
   125      },
   126
   127      revert: function() {
>  128          var self = this;
   129          var postData = {
   130              'selectedIdentities': this.selectedIdentities(),
   131              'selectedCards': this.selectedCards()
   132          };
```
After:

```
   206              });
   207      },
   208
   209      revert: function() {
>  210          var self = this;
   211          if (!this.canSubmit()) {
   212              return;
   213          }
   214          var confirm = arches.translations.graphDesignerPermissionsResetConfirm;
```

## 36. nodebb: `CG-SEC-105` (known_but_new)

- Commit: [9d122948cf](https://github.com/NodeBB/NodeBB/commit/9d122948cf783fc72c8c01c7aab0f42b2561b3c3), file `test/user.js`
- Truth: **known (equal)**, old line 1999, new line 2030
- Schemes that disagree with the truth: `codeguard` (mispaired), `line_text` (mispaired), `sonar` (false_new)

Before:

```
  1995
  1996  		it('should fail to add user to queue if username is taken', async () => {
  1997  			const { body } = await helpers.registerUser({
  1998  				username: 'rejectme',
> 1999  				password: '123456',
  2000  				'password-confirm': '123456',
  2001  				email: '<script>alert("ok")<script>reject@me.com',
  2002  				gdpr_consent: true,
  2003  			});
```
After:

```
  2026
  2027  		it('should fail to add user to queue if username is taken', async () => {
  2028  			const { body } = await helpers.registerUser({
  2029  				username: 'rejectme',
> 2030  				password: '123456',
  2031  				'password-confirm': '123456',
  2032  				email: '<script>alert("ok")<script>reject@me.com',
  2033  				gdpr_consent: true,
  2034  			});
```

## 37. calcom: `CG-SEC-105` (known_but_new)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **known (equal)**, old line 1267, new line 1601
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
  1263                        {
  1264                          type: appStoreMetadata.googlecalendar.type,
  1265                          uid: "MOCK_ID",
  1266                          meetingId: "MOCK_ID",
> 1267                          meetingPassword: "MOCK_PASSWORD",
  1268                          meetingUrl: "https://UNUSED_URL",
  1269                          externalCalendarId: "existing-event-type@example.com",
  1270                          credentialId: undefined,
  1271                        },
```
After:

```
  1597                        {
  1598                          type: appStoreMetadata.googlecalendar.type,
  1599                          uid: "MOCK_ID",
  1600                          meetingId: "MOCK_ID",
> 1601                          meetingPassword: "MOCK_PASSWORD",
  1602                          meetingUrl: "https://UNUSED_URL",
  1603                          externalCalendarId: "existing-event-type@example.com",
  1604                          credentialId: undefined,
  1605                        },
```

## 38. nodebb: `CG-SEC-105` (known_but_new)

- Commit: [b8d9cf9d1e](https://github.com/NodeBB/NodeBB/commit/b8d9cf9d1ee03115d28b3548911e9076a275311a), file `test/user.js`
- Truth: **known (equal)**, old line 2318, new line 2335
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
  2314  				const token = await db.get(`invitation:uid:${inviterUid}:invited:${email}`);
  2315
  2316  				const { body } = await helpers.registerUser({
  2317  					username: 'invite5',
> 2318  					password: '123456',
  2319  					'password-confirm': '123456',
  2320  					email: email,
  2321  					gdpr_consent: true,
  2322  					token: token,
```
After:

```
  2331  				const token = await db.get(`invitation:uid:${inviterUid}:invited:${email}`);
  2332
  2333  				const { body } = await helpers.registerUser({
  2334  					username: 'invite5',
> 2335  					password: '123456',
  2336  					'password-confirm': '123456',
  2337  					email: email,
  2338  					gdpr_consent: true,
  2339  					token: token,
```

## 39. nodebb: `CG-SEC-105` (known_but_new)

- Commit: [331599fe89](https://github.com/NodeBB/NodeBB/commit/331599fe89bed8c8ae80199efafeee9e81f72dbf), file `test/topics/crossposts.js`
- Truth: **known (equal)**, old line 660, new line 678
- Schemes that disagree with the truth: `codeguard` (false_new), `github` (false_new), `line_text` (false_new)

Before:

```
   656  			});
   657
   658  			it('should send an Announce to the topic author when crossposted to a local category', async () => {
   659  				const username = utils.generateUUID().slice(0, 8);
>  660  				const crossposter = await user.create({ username, password: '123456' });
   661  				const login = await helpers.loginUser(username, '123456');
   662  				activitypub._sent.clear();
   663
   664  				const crosspostCid = (await categories.create({ name: utils.generateUUID().slice(0, 8) })).cid;
```
After:

```
   674  			});
   675
   676  			it('should send an Announce to the topic author when crossposted to a local category', async () => {
   677  				const username = utils.generateUUID().slice(0, 8);
>  678  				const crossposter = await user.create({ username, password: '123456' });
   679  				const login = await helpers.loginUser(username, '123456');
   680  				activitypub._sent.clear();
   681
   682  				const crosspostCid = (await categories.create({ name: utils.generateUUID().slice(0, 8) })).cid;
```

## 40. openlibrary: `CG-SEC-001` (known_but_new)

- Commit: [f5aff19fb7](https://github.com/internetarchive/openlibrary/commit/f5aff19fb7d0c27f3bb91f08db81a8750bae604a), file `openlibrary/tests/core/test_bookshelves_events_async.py`
- Truth: **known (equal)**, old line 56, new line 144
- Schemes that disagree with the truth: `codeguard` (false_new)

Before:

```
    52              await conn.execute(
    53                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    54                  {"u": "alice", "w": 104, "e": 1, "t": BookshelfEvent.START, "d": "2026-05-01"},
    55              )
>   56              await conn.execute(
    57                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
    58                  {"u": "alice", "w": 105, "e": 1, "t": BookshelfEvent.FINISH, "d": "2025-05-01"},
    59              )
    60
```
After:

```
   140              await conn.execute(
   141                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   142                  {"u": "alice", "w": 104, "e": 1, "t": BookshelfEvent.START, "d": "2026-05-01"},
   143              )
>  144              await conn.execute(
   145                  f"INSERT INTO {BookshelvesEvents.TABLENAME} (username, work_id, edition_id, event_type, event_date) VALUES (%(u)s, %(w)s, %(e)s, %(t)s, %(d)s)",
   146                  {"u": "alice", "w": 105, "e": 1, "t": BookshelfEvent.FINISH, "d": "2025-05-01"},
   147              )
   148
```

## 41. hoppscotch: `CG-PERF-101` (new_but_matched)

- Commit: [803e4633a2](https://github.com/hoppscotch/hoppscotch/commit/803e4633a27be10d80e752d62bd0dab09ed2924a), file `packages/hoppscotch-backend/src/team-collection/team-collection.service.ts`
- Truth: **new**, new line 131
- Schemes that disagree with the truth: `codeguard` (false_known), `github` (false_known), `line_text` (false_known), `sonar` (false_known)

After:

```
   127        },
   128      });
   129
   130      for (const coll of childrenCollection) {
>  131        const result = await this.exportCollectionToJSONObject(teamID, coll.id);
   132        if (E.isLeft(result)) return E.left(result.left);
   133
   134        childrenCollectionObjects.push(result.right);
   135      }
```

Diff near the line:

```diff
@@ -106,35 +106,32 @@ export class TeamCollectionService {
    *
    * @param teamID The Team ID
    * @param collectionID The Collection ID
-   * @param withChildren Whether to include child collections and their requests
    * @returns A JSON string containing all the contents of a collection
    */
   async exportCollectionToJSONObject(
     teamID: string,
     collectionID: string,
-    withChildren: boolean = true,
   ): Promise<E.Right<CollectionFolder> | E.Left<string>> {
     const collection = await this.getCollection(collectionID);
     if (E.isLeft(collection)) return E.left(TEAM_INVALID_COLL_ID);

     const childrenCollectionObjects = [];
-    if (withChildren) {
-      const childrenCollection = await this.prisma.teamCollection.findMany({
-        where: {
-          teamID,
-          parentID: collectionID,
-        },
-        orderBy: {
-          orderIndex: 'asc',
-        },
-      });

-      for (const coll of childrenCollection) {
-        const result = await this.exportCollectionToJSONObject(teamID, coll.id);
-        if (E.isLeft(result)) return E.left(result.left);
+    const childrenCollection = await this.prisma.teamCollection.findMany({
+      where: {
+        teamID,
+        parentID: collectionID,
+      },
+      orderBy: {
+        orderIndex: 'asc',
+      },
+    });

... (11 more lines)
```

## 42. ckan: `CG-QUAL-104` (new_but_matched)

- Commit: [7a60264189](https://github.com/ckan/ckan/commit/7a60264189f543fba04043d2193b09f545a6ef32), file `ckan/public-midnight-blue/base/javascript/modules/data-viewer.js`
- Truth: **new**, new line 27
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    23      },
    24
    25      _onLoad: function() {
    26        var self = this;
>   27        var loc = document.head.querySelector(['meta[name=site-root]'])?.content;
    28        // see if page is in part of the same domain
    29        if (this.el.attr('src').substring(0, loc.length) === loc) {
    30          this._recalibrate();
    31          setTimeout(function() {
```

Diff near the line:

```diff
@@ -24,7 +24,7 @@ this.ckan.module('data-viewer', function (jQuery) {

     _onLoad: function() {
       var self = this;
-      var loc = $('body').data('site-root');
+      var loc = document.head.querySelector(['meta[name=site-root]'])?.content;
       // see if page is in part of the same domain
       if (this.el.attr('src').substring(0, loc.length) === loc) {
         this._recalibrate();

```

## 43. pgadmin: `CG-QUAL-101` (new_but_matched)

- Commit: [a4bdcff7dc](https://github.com/pgadmin-org/pgadmin4/commit/a4bdcff7dc65e1b667b981574a7c7263bc84afd2), file `web/pgadmin/misc/cloud/static/js/cloud_components.jsx`
- Truth: **new**, new line 58
- Schemes that disagree with the truth: `codeguard` (false_known)

After:

```
    54  export function FinalSummary(props) {
    55    let summary = [],
    56      summaryHeader = ['Cloud Details', 'Version and Instance Details', 'Storage Details', 'Database Details'];
    57
>   58    if(props.cloudProvider == 'starfleet') {
    59      summaryHeader = ['Cloud Details', 'Network Connectivity'];
    60      summary = getStarfleetSummary(props.cloudProvider, props.instanceData, props.databaseData);
    61    }else if(props.cloudProvider == 'azure') {
    62      summaryHeader.push('Network Connectivity','Availability');
```

Diff near the line:

```diff
@@ -54,7 +55,10 @@ export function FinalSummary(props) {
   let summary = [],
     summaryHeader = ['Cloud Details', 'Version and Instance Details', 'Storage Details', 'Database Details'];

-  if(props.cloudProvider == 'azure') {
+  if(props.cloudProvider == 'starfleet') {
+    summaryHeader = ['Cloud Details', 'Network Connectivity'];
+    summary = getStarfleetSummary(props.cloudProvider, props.instanceData, props.databaseData);
+  }else if(props.cloudProvider == 'azure') {
     summaryHeader.push('Network Connectivity','Availability');
     summary = getAzureSummary(props.cloudProvider, props.instanceData, props.databaseData);
   }else if(props.cloudProvider == 'google') {

```

## 44. intelowl: `CG-SEC-105` (new_but_matched)

- Commit: [80107d6f05](https://github.com/intelowlproject/IntelOwl/commit/80107d6f05e8c1ca1e9ca1d0a937e5df400b7fe0), file `frontend/src/components/auth/utils/validator.jsx`
- Truth: **new**, new line 24
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    20      errors.password = "Required";
    21    } else if (password.length < 12) {
    22      errors.password = "Must be 12 characters or more";
    23    } else if (!PASSWORD_REGEX.test(password)) {
>   24      errors.password = "The password cannot be entirely numeric";
    25    }
    26    return errors;
    27  }
    28
```

Diff near the line:

```diff
@@ -21,8 +21,7 @@ export function PasswordValidator(password) {
   } else if (password.length < 12) {
     errors.password = "Must be 12 characters or more";
   } else if (!PASSWORD_REGEX.test(password)) {
-    errors.password =
-      "The password is entirely numeric or contains special characters";
+    errors.password = "The password cannot be entirely numeric";
   }
   return errors;
 }

```

## 45. intelowl: `CG-SEC-105` (new_but_matched)

- Commit: [80107d6f05](https://github.com/intelowlproject/IntelOwl/commit/80107d6f05e8c1ca1e9ca1d0a937e5df400b7fe0), file `frontend/tests/components/auth/utils/validator.test.jsx`
- Truth: **new**, new line 45
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    41    });
    42    test("Invalid password", () => {
    43      const numericPassword = "123456123456";
    44      expect(PasswordValidator(numericPassword)).toEqual({
>   45        password: "The password cannot be entirely numeric",
    46      });
    47    });
    48    test("Password with special characters is valid", () => {
    49      const password = "intelowlpassword$";
```

Diff near the line:

```diff
@@ -42,14 +42,12 @@ describe("Password", () => {
   test("Invalid password", () => {
     const numericPassword = "123456123456";
     expect(PasswordValidator(numericPassword)).toEqual({
-      password:
-        "The password is entirely numeric or contains special characters",
+      password: "The password cannot be entirely numeric",
     });
+  });
+  test("Password with special characters is valid", () => {
     const password = "intelowlpassword$";
-    expect(PasswordValidator(password)).toEqual({
-      password:
-        "The password is entirely numeric or contains special characters",
-    });
+    expect(PasswordValidator(password)).toEqual({});
   });
 });


```

## 46. arches: `CG-QUAL-104` (new_but_matched)

- Commit: [2e02ce6e61](https://github.com/archesproject/arches/commit/2e02ce6e61999d93c10b05d853ae08f1912fa294), file `arches/app/media/js/views/graph/permission-designer.js`
- Truth: **new**, new line 148
- Schemes that disagree with the truth: `codeguard` (false_known), `github` (false_known), `sonar` (false_known)

After:

```
   144                  .done(function(res) {
   145                      var byNodegroup = {};
   146                      res.forEach(function(nodegroup) {
   147                          byNodegroup[nodegroup.nodegroup_id] = nodegroup;
>  148                          var card = _.find(self.cardList, function(card) {
   149                              return card.model.nodegroup_id() === nodegroup.nodegroup_id;
   150                          });
   151                          if (!card) {
   152                              return;
```

Diff near the line:

```diff
@@ -70,62 +99,82 @@ import PermissionSettingsForm from 'views/graph/permission-manager/permission-se
                         self.updatePermissions();
                     });
                 })
-                .fail(function(err) {
-                    console.log(err);
+                .fail(function(response) {
+                    showError(response.responseJSON, arches.translations.graphDesignerPermissionsLoadError);
+                })
+                .always(function() {
+                    self.loading(false);
                 });
         };

+        var setCardPerms = function(card, perms, literal) {
+            card.perms(perms);
+            card.permsLiteral(literal);
+            if (card.type === 'card' && card.children && card.children.length > 0) {
+                card.children.forEach(function(child) {
+                    if (child.type === 'node' && child.perms) {
+                        child.perms(perms);
+                    }
+                });
+            }
+        };
+
         this.updatePermissions = function() {
-            var item = self.identityList.selectedItems()[0];
-            var nodegroupIds = [];
+            var identity = self.identityList.selectedItems()[0];

-            if (item) {
-                self.cardList.forEach(function(item) {
-                    nodegroupIds.push(item.model.nodegroup_id());
+            if (!identity || !self.cardList) {
+                self.permissionsByNodegroup({});
+                (self.cardList || []).forEach(function(card) {
+                    setCardPerms(card, [], '');
                 });
-                $.ajax({
... (91 more lines)
```

## 47. geonode: `CG-SEC-002` (new_but_matched)

- Commit: [6f00ca5b66](https://github.com/GeoNode/geonode/commit/6f00ca5b66b2459cf3a6556434d476810cabe0d4), file `geonode/geoserver/gwc.py`
- Truth: **new**, new line 50
- Schemes that disagree with the truth: `line_text` (false_known)

After:

```
    46          else:
    47              logger.debug(f"{r.request.method} response: code:{r.status_code} --> {len(r.text)} bytes")
    48
    49      def _get(self, urlpath):
>   50          _user, _password = ogc_server_settings.credentials
    51
    52          url = f"{self.base_url}{urlpath}"
    53          r = requests.get(url=url, auth=HTTPBasicAuth(_user, _password), timeout=30)
    54          self.__log_response(r)
```

Diff near the line:

```diff
@@ -36,15 +36,40 @@ class GWCClient:
     A GeoWebCache REST client for interacting with the GWC API.
     """

-    def __init__(self) -> None:
+    def __init__(self, **kwargs) -> None:
         self.base_url = f"{ogc_server_settings.LOCATION}gwc/rest/"
+        self.debug = kwargs.get("debug", False)
+
+    def __log_response(self, r):
+        if self.debug:
+            logger.debug(f'{r.request.method} response: code:{r.status_code} --> "{r.text}"')
+        else:
+            logger.debug(f"{r.request.method} response: code:{r.status_code} --> {len(r.text)} bytes")
+
+    def _get(self, urlpath):
+        _user, _password = ogc_server_settings.credentials
+
+        url = f"{self.base_url}{urlpath}"
+        r = requests.get(url=url, auth=HTTPBasicAuth(_user, _password), timeout=30)
+        self.__log_response(r)
+        return r

     def _post(self, urlpath, data):
         _user, _password = ogc_server_settings.credentials

         url = f"{self.base_url}{urlpath}"
         r = requests.post(url=url, data=data, auth=HTTPBasicAuth(_user, _password), timeout=30)
-        logger.debug(f'POST response: code:{r.status_code} --> "{r.text}"')
+        self.__log_response(r)
+        return r
+
+    def _put(self, urlpath, data):
+        _user, _password = ogc_server_settings.credentials
+
+        url = f"{self.base_url}{urlpath}"
+        r = requests.put(
+            url=url, data=data, headers={"Content-Type": "text/xml"}, auth=HTTPBasicAuth(_user, _password), timeout=30
+        )
+        self.__log_response(r)
... (3 more lines)
```

## 48. hoppscotch: `CG-QUAL-101` (new_but_matched)

- Commit: [342d0cbdf0](https://github.com/hoppscotch/hoppscotch/commit/342d0cbdf0c5435b715dc9f1917b851e413e08e3), file `packages/hoppscotch-common/src/lib/sync/collections/index.ts`
- Truth: **new**, new line 384
- Schemes that disagree with the truth: `codeguard` (false_known), `line_text` (false_known)

After:

```
   380          ) as HoppCollection
   381      )
   382
   383      const localCollections =
>  384        collectionType == "REST"
   385          ? restCollectionStore.value.state
   386          : graphqlCollectionStore.value.state
   387
   388      const mergedCollections = mergeCollections(localCollections, fetchedCollections)
```

Diff near the line:

```diff
@@ -269,26 +371,26 @@ async function loadUserCollections(collectionType: "REST" | "GQL") {
         ExportedUserCollectionGQL | ExportedUserCollectionREST
       >
     ).map((collection) => ({ v: 1, ...collection }))
+
+    const fetchedCollections = exportedCollections.map(
+      (collection) =>
+        exportedCollectionToHoppCollection(
+          collection,
+          collectionType
+        ) as HoppCollection
+    )
+
+    const localCollections =
+      collectionType == "REST"
+        ? restCollectionStore.value.state
+        : graphqlCollectionStore.value.state
+
+    const mergedCollections = mergeCollections(localCollections, fetchedCollections)
+
     runDispatchWithOutSyncing(() => {
       collectionType == "REST"
-        ? setRESTCollections(
-            exportedCollections.map(
-              (collection) =>
-                exportedCollectionToHoppCollection(
-                  collection,
-                  "REST"
-                ) as HoppCollection
-            )
-          )
-        : setGraphqlCollections(
-            exportedCollections.map(
-              (collection) =>
-                exportedCollectionToHoppCollection(
-                  collection,
-                  "GQL"
-                ) as HoppCollection
-            )
-          )
... (6 more lines)
```

## 49. ghost: `CG-PERF-101` (new_but_matched)

- Commit: [0f623f3f5d](https://github.com/TryGhost/Ghost/commit/0f623f3f5daf914e9896e29cfe28bfbce0f0a8e3), file `tools/scripts/test/public-apps.test.ts`
- Truth: **new**, new line 67
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    63    it('holds for every public app in the repo right now', async () => {
    64      const defaults = (await readDefaults()) as Record<string, { version: string }>;
    65
    66      for (const app of PUBLIC_APPS) {
>   67        const { version } = await readJson<{ version: string }>(
    68          join(ROOT_DIR, app.path, 'package.json'),
    69        );
    70
    71        assert.strictEqual(
```

Diff near the line:

```diff
@@ -61,15 +61,17 @@ describe('the major.minor invariant', () => {
   // If the repo ever violates it, one of those two is broken — or someone
   // hand-edited a version without running "pnpm ship".
   it('holds for every public app in the repo right now', async () => {
-    const defaults = await readDefaults();
+    const defaults = (await readDefaults()) as Record<string, { version: string }>;

     for (const app of PUBLIC_APPS) {
-      const { version } = await readJson(join(ROOT_DIR, app.path, 'package.json'));
+      const { version } = await readJson<{ version: string }>(
+        join(ROOT_DIR, app.path, 'package.json'),
+      );

       assert.strictEqual(
-        defaults[app.configKey].version,
+        defaults[app.configKey]?.version,
         majorMinor(version),
-        `${app.packageName}: package.json is ${version}, defaults.json says ${defaults[app.configKey].version}`,
+        `${app.packageName}: package.json is ${version}, defaults.json says ${defaults[app.configKey]?.version}`,
       );
     }
   });

```

## 50. immich: `CG-PERF-101` (new_but_matched)

- Commit: [e66f2c7615](https://github.com/immich-app/immich/commit/e66f2c7615bacbe6a9b156e300fc182e4d1a4fa3), file `server/src/services/person.service.ts`
- Truth: **new**, new line 162
- Schemes that disagree with the truth: `codeguard` (false_known), `github` (false_known), `sonar` (false_known)

After:

```
   158        if (!assetFace) {
   159          continue;
   160        }
   161
>  162        await this.personRepository.update({ ownerId, personGroupId, faceAssetId: assetFace.id });
   163        jobs.push({ name: JobName.PersonGenerateThumbnail, data: { ownerId, personGroupId } });
   164      }
   165
   166      await this.jobRepository.queueAll(jobs);
```

Diff near the line:

```diff
@@ -155,10 +155,12 @@ export class PersonService extends BaseService {
     for (const { ownerId, personGroupId } of changeFeaturePhoto) {
       const assetFace = await this.personRepository.getRandomFace(personGroupId);

-      if (assetFace) {
-        await this.personRepository.update({ ownerId, personGroupId, faceAssetId: assetFace.id });
-        jobs.push({ name: JobName.PersonGenerateThumbnail, data: { ownerId, personGroupId } });
+      if (!assetFace) {
+        continue;
       }
+
+      await this.personRepository.update({ ownerId, personGroupId, faceAssetId: assetFace.id });
+      jobs.push({ name: JobName.PersonGenerateThumbnail, data: { ownerId, personGroupId } });
     }

     await this.jobRepository.queueAll(jobs);

```

## 51. arches: `CG-QUAL-104` (new_but_matched)

- Commit: [2e02ce6e61](https://github.com/archesproject/arches/commit/2e02ce6e61999d93c10b05d853ae08f1912fa294), file `arches/app/media/js/views/graph/permission-manager/permission-settings-form.js`
- Truth: **new**, new line 30
- Schemes that disagree with the truth: `codeguard` (false_known), `line_text` (false_known)

After:

```
    26      * @memberof PermissionSettingsForm.prototype
    27      * @param {boolean} options.selection - the selected item, either a {@link CardModel} or a {@link NodeModel}
    28      */
    29      initialize: function(options) {
>   30          var self = this;
    31          this.selectedIdentities = options.selectedIdentities;
    32          this.identityList = options.identityList;
    33          this.selectedCards = options.selectedCards;
    34          this.permissionsByNodegroup = options.permissionsByNodegroup || ko.observable({});
```

Diff near the line:

```diff
@@ -19,9 +27,13 @@ var PermissionSettingsForm = Backbone.View.extend({
     * @param {boolean} options.selection - the selected item, either a {@link CardModel} or a {@link NodeModel}
     */
     initialize: function(options) {
+        var self = this;
         this.selectedIdentities = options.selectedIdentities;
         this.identityList = options.identityList;
         this.selectedCards = options.selectedCards;
+        this.permissionsByNodegroup = options.permissionsByNodegroup || ko.observable({});
+        this.loading = options.loading || ko.observable(false);
+        this.alert = options.alert || ko.observable();
         this.noAccessPerm = undefined;
         this.whiteListPerms = [];
         this.groupedNodeList = options.groupedNodeList;
```

## 52. readthedocs: `CG-SEC-002` (new_but_matched)

- Commit: [857138d4d9](https://github.com/readthedocs/readthedocs.org/commit/857138d4d9659a62ce46f52a358f535b6ffeef75), file `readthedocs/rtd_tests/tests/test_api.py`
- Truth: **new**, new line 331
- Schemes that disagree with the truth: `github` (false_known), `line_text` (false_known)

After:

```
   327          )
   328          assert not project.has_feature(Feature.USE_BUILD_ISOLATED)
   329
   330          client = APIClient()
>  331          _, build_api_key = BuildAPIKey.objects.create_key(project)
   332          client.credentials(HTTP_AUTHORIZATION=f"Token {build_api_key}")
   333
   334          resp = client.patch(
   335              "/api/v2/build/{}/".format(build.pk),
```

Diff near the line:

```diff
@@ -315,6 +315,30 @@ class APIBuildTests(TestCase):
             Build.objects.get(pk=build_two.pk).readthedocs_yaml_config.pk,
         )

+    @mock.patch("readthedocs.api.v2.views.model_views.run_post_build_tasks")
+    def test_finishing_uploaded_build_runs_post_build_tasks(self, run_post_build_tasks):
+        project = Project.objects.get(pk=1)
+        version = project.versions.first()
+        build = Build.objects.create(
+            project=project,
+            version=version,
+            state=BUILD_STATE_TRIGGERED,
+            is_uploaded=True,
+        )
+        assert not project.has_feature(Feature.USE_BUILD_ISOLATED)
+
+        client = APIClient()
+        _, build_api_key = BuildAPIKey.objects.create_key(project)
+        client.credentials(HTTP_AUTHORIZATION=f"Token {build_api_key}")
+
+        resp = client.patch(
+            "/api/v2/build/{}/".format(build.pk),
+            {"state": BUILD_STATE_FINISHED},
+            format="json",
+        )
+        assert resp.status_code == status.HTTP_200_OK
+        run_post_build_tasks.delay.assert_called_once_with(build_pk=build.pk)
+
     def test_response_building(self):
         """The ``view docs`` attr should return a link to the dashboard."""
         client = APIClient()

```

## 53. openlibrary: `CG-QUAL-104` (new_but_matched)

- Commit: [53015559eb](https://github.com/internetarchive/openlibrary/commit/53015559ebcd126850e7b07792ebc7bcfa847919), file `openlibrary/plugins/openlibrary/js/graphs/plot.js`
- Truth: **new**, new line 20
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    16   * - http://localhost:8080/subjects/fantasy#sort=date_published&ebooks=true
    17   * - http://localhost:8080/publishers/Barnes_&_Noble
    18   */
    19  export function loadEditionsGraph() {
>   20      var data, options, placeholder, plot, dateFrom, dateTo, previousPoint;
    21      data = [{ data: JSON.parse(document.getElementById('graph-json-chartPubHistory').textContent) }];
    22      options = {
    23          series: {
    24              bars: {
```

Diff near the line:

```diff
@@ -17,9 +17,8 @@ import 'flot/jquery.flot.time.js';
  * - http://localhost:8080/publishers/Barnes_&_Noble
  */
 export function loadEditionsGraph() {
-    var data, options, placeholder,
-        plot, dateFrom, dateTo, previousPoint;
-    data = [{data: JSON.parse(document.getElementById('graph-json-chartPubHistory').textContent)}];
+    var data, options, placeholder, plot, dateFrom, dateTo, previousPoint;
+    data = [{ data: JSON.parse(document.getElementById('graph-json-chartPubHistory').textContent) }];
     options = {
         series: {
             bars: {
```

## 54. calcom: `CG-SEC-105` (new_but_matched)

- Commit: [ab21c7f805](https://github.com/calcom/cal.com/commit/ab21c7f805a089fa3a11ffd61c4a9aecc349c16c), file `packages/features/bookings/lib/handleNewBooking/test/reschedule.test.ts`
- Truth: **new**, new line 806
- Schemes that disagree with the truth: `codeguard` (false_known), `github` (false_known), `line_text` (false_known)

After:

```
   802                    {
   803                      type: appStoreMetadata.dailyvideo.type,
   804                      uid: "MOCK_ID",
   805                      meetingId: "MOCK_ID",
>  806                      meetingPassword: "MOCK_PASS",
   807                      meetingUrl: "http://mock-dailyvideo.example.com",
   808                    },
   809                    {
   810                      type: appStoreMetadata.googlecalendar.type,
```

Diff near the line:

```diff
@@ -690,8 +660,201 @@ describe("handleNewBooking", () => {
       );

       describe("Event Type that requires confirmation", () => {
-        // NOTE: Tests for BOOKING_REQUESTED webhook have been moved to the new webhook architecture test suite
-        // See packages/features/webhooks/lib/__tests__/ for tests using the producer/consumer pattern
+        test(
+          `should reschedule a booking that requires confirmation in PENDING state - When a booker(who is not the organizer himself) is doing the reschedule
+          1. Should cancel the existing booking
+          2. Should delete existing calendar invite and Video meeting
+          2. Should create a new booking in the database in PENDING state
+          3. Should send BOOKING Requested scenario emails to the booker as well as organizer
+          4. Should trigger BOOKING_REQUESTED webhook instead of BOOKING_RESCHEDULED
+    `,
+          async ({ emails }) => {
+            const handleNewBooking = getNewBookingHandler();
+            const subscriberUrl = "http://my-webhook.example.com";
+            const booker = getBooker({
+              email: "booker@example.com",
+              name: "Booker",
+            });
+
+            const organizer = getOrganizer({
+              name: "Organizer",
+              email: "organizer@example.com",
+              id: 101,
+              schedules: [TestData.schedules.IstWorkHours],
+              credentials: [getGoogleCalendarCredential()],
+              selectedCalendars: [TestData.selectedCalendars.google],
+            });
+            const { dateString: plus1DateString } = getDate({ dateIncrement: 1 });
+            const uidOfBookingToBeRescheduled = "n5Wv3eHgconAED2j4gcVhP";
+
+            const scenarioData = getScenarioData({
+              webhooks: [
+                {
+                  userId: organizer.id,
+                  eventTriggers: ["BOOKING_CREATED"],
+                  subscriberUrl,
+                  active: true,
... (164 more lines)
```

## 55. ckan: `CG-QUAL-104` (new_but_matched)

- Commit: [7a60264189](https://github.com/ckan/ckan/commit/7a60264189f543fba04043d2193b09f545a6ef32), file `ckan/public/base/javascript/modules/data-viewer.js`
- Truth: **new**, new line 27
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
    23      },
    24
    25      _onLoad: function() {
    26        var self = this;
>   27        var loc = document.head.querySelector(['meta[name=site-root]'])?.content;
    28        // see if page is in part of the same domain
    29        if (this.el.attr('src').substring(0, loc.length) === loc) {
    30          this._recalibrate();
    31          setTimeout(function() {
```

Diff near the line:

```diff
@@ -24,7 +24,7 @@ this.ckan.module('data-viewer', function (jQuery) {

     _onLoad: function() {
       var self = this;
-      var loc = $('body').data('site-root');
+      var loc = document.head.querySelector(['meta[name=site-root]'])?.content;
       // see if page is in part of the same domain
       if (this.el.attr('src').substring(0, loc.length) === loc) {
         this._recalibrate();

```

## 56. calcom: `CG-SEC-105` (new_but_matched)

- Commit: [1660adeb53](https://github.com/calcom/cal.com/commit/1660adeb537a3524290c6885c6b9feca63cf675b), file `scripts/seed.ts`
- Truth: **new**, new line 1008
- Schemes that disagree with the truth: `codeguard` (false_known), `github` (false_known), `line_text` (false_known), `sonar` (false_known)

After:

```
  1004    const admin = await createUserAndEventType({
  1005      user: {
  1006        email: "admin@example.com",
  1007        /** To comply with admin password requirements  */
> 1008        password: "ADMINadmin2022!",
  1009        username: "admin",
  1010        name: "Admin Example",
  1011        role: "ADMIN",
  1012      },
```

Diff near the line:

```diff
@@ -1248,6 +1001,32 @@ async function main() {
     },
   });

+  const admin = await createUserAndEventType({
+    user: {
+      email: "admin@example.com",
+      /** To comply with admin password requirements  */
+      password: "ADMINadmin2022!",
+      username: "admin",
+      name: "Admin Example",
+      role: "ADMIN",
+    },
+  });
+
+  const clientId = process.env.SEED_OAUTH2_CLIENT_ID;
+  const clientSecret = process.env.SEED_OAUTH2_CLIENT_SECRET_HASHED;
+
+  if (clientId && clientSecret) {
+    await createOAuthClientForUser(admin.id, {
+      clientId,
+      clientSecret,
+      name: "atoms examples app oauth 2 client",
+      purpose: "test atoms examples app with oauth 2",
+      redirectUri: "http://localhost:4321",
+      websiteUrl: "http://localhost:4321",
+      enablePkce: false,
+    });
+  }
+
   if (process.env.E2E_TEST_CALCOM_QA_EMAIL && process.env.E2E_TEST_CALCOM_QA_PASSWORD) {
     await createUserAndEventType({
       user: {

```

## 57. hoppscotch: `CG-QUAL-101` (new_but_matched)

- Commit: [863b1b29a8](https://github.com/hoppscotch/hoppscotch/commit/863b1b29a803f6c456b04dd82d19a53c7afc9102), file `packages/hoppscotch-common/src/lib/sync/collections/index.ts` (was `packages/hoppscotch-selfhost-web/src/platform/collections/desktop/index.ts`)
- Truth: **new**, new line 511
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
   507            collectionType == "REST"
   508              ? editRESTFolder(updatedCollectionLocalPath, partialUpdate)
   509              : editGraphqlFolder(updatedCollectionLocalPath, partialUpdate)
   510          } else {
>  511            collectionType == "REST"
   512              ? editRESTCollection(
   513                  parseInt(updatedCollectionLocalPath),
   514                  partialUpdate
   515                )
```

Diff near the line:

```diff
@@ -458,45 +454,71 @@ function setupUserCollectionUpdatedSubscription() {

   userCollectionUpdated$.subscribe((res) => {
     if (E.isRight(res)) {
-      const collectionType = res.right.userCollectionUpdated.type
+      const {
+        id: updatedCollectionBackendID,
+        title,
+        type: collectionType,
+        data,
+      } = res.right.userCollectionUpdated

       const { collectionStore } = getStoreByCollectionType(collectionType)

-      const updatedCollectionBackendID = res.right.userCollectionUpdated.id
       const updatedCollectionLocalPath = getCollectionPathFromCollectionID(
         updatedCollectionBackendID,
         collectionStore.value.state
       )

-      const isFolder =
-        updatedCollectionLocalPath &&
-        updatedCollectionLocalPath.split("/").length > 1
+      if (!updatedCollectionLocalPath) return

-      // updated collection is a folder
-      if (isFolder) {
-        runDispatchWithOutSyncing(() => {
-          collectionType == "REST"
-            ? editRESTFolder(updatedCollectionLocalPath, {
-                name: res.right.userCollectionUpdated.title,
-              })
-            : editGraphqlFolder(updatedCollectionLocalPath, {
-                name: res.right.userCollectionUpdated.title,
-              })
-        })
+      const isFolder = updatedCollectionLocalPath.split("/").length > 1
+
+      // Carry auth, headers, variables, and scripts from the data payload
+      const {
... (59 more lines)
```

## 58. ghost: `CG-PERF-101` (new_but_matched)

- Commit: [7da91e095b](https://github.com/TryGhost/Ghost/commit/7da91e095b2803c62bc67fe70f2c4f0d114846d9), file `tools/scripts/test/ci-path-filters.test.js`
- Truth: **new**, new line 69
- Schemes that disagree with the truth: `codeguard` (false_known), `line_text` (false_known)

After:

```
    65      const docs = await getFilterPatterns('docs');
    66      assert.ok(docs.some((pattern) => picomatch(pattern, { dot: true })(inventory)));
    67
    68      for (const filterName of ['core', 'any-code', 'e2e']) {
>   69        const patterns = await getFilterPatterns(filterName);
    70        const positives = patterns.filter((pattern) => !pattern.startsWith('!'));
    71        const exclusions = patterns.filter((pattern) => pattern.startsWith('!'));
    72        const matches = (path) =>
    73          (positives.length === 0 ||
```

Diff near the line:

```diff
@@ -56,6 +60,83 @@ describe('CI path filters', () => {
     assert.ok(e2e.includes('!**/*.mdx'));
   });

+  it('treats the service inventory as docs and keeps code checks for mixed changes', async () => {
+    const inventory = 'ghost/core/server/services/service-inventory.yaml';
+    const docs = await getFilterPatterns('docs');
+    assert.ok(docs.some((pattern) => picomatch(pattern, { dot: true })(inventory)));
+
+    for (const filterName of ['core', 'any-code', 'e2e']) {
+      const patterns = await getFilterPatterns(filterName);
+      const positives = patterns.filter((pattern) => !pattern.startsWith('!'));
+      const exclusions = patterns.filter((pattern) => pattern.startsWith('!'));
+      const matches = (path) =>
+        (positives.length === 0 ||
+          positives.some((pattern) => picomatch(pattern, { dot: true })(path))) &&
+        exclusions.every((pattern) => picomatch(pattern, { dot: true })(path));
+      const metadata = [inventory, 'ghost/core/server/services/README.md'];
+
+      assert.strictEqual(metadata.some(matches), false, filterName);
+      for (const runtime of [
+        'ghost/core/server/services/identity-tokens/index.ts',
+        'ghost/core/server/services/other-metadata.yaml',
+        '.github/workflows/ci.yml',
+      ]) {
+        assert.strictEqual([...metadata, runtime].some(matches), true, `${filterName}: ${runtime}`);
+      }
+    }
+
+    const anyCode = await getFilterPatterns('any-code');
+    assert.ok(
+      anyCode.every((pattern) =>
+        picomatch(pattern, { dot: true })(
+          'ghost/test/unit/server/services/service-inventory.test.ts',
+        ),
+      ),
+      'Changes to the inventory validator must still run code checks',
+    );
+  });
+
... (45 more lines)
```

## 59. arches: `CG-QUAL-104` (new_but_matched)

- Commit: [ac6a5ab690](https://github.com/archesproject/arches/commit/ac6a5ab6907f92256a1ebdbc373de7cabb41e3b0), file `arches/app/media/js/views/graph-designer.js`
- Truth: **new**, new line 793
- Schemes that disagree with the truth: `sonar` (false_known)

After:

```
   789              }
   790          };
   791
   792          // only follow the Cards tab when its selection changed, so a multi-selection survives tab switches
>  793          var lastSyncedCardSelection;
   794          var updatePermissionCardSelection = function() {
   795              var cardSelection = viewModel.cardTree.selection();
   796              if (cardSelection === lastSyncedCardSelection) {
   797                  return;
```

Diff near the line:

```diff
@@ -789,12 +789,19 @@ var GraphDesignerView = BaseManagerView.extend({
             }
         };

+        // only follow the Cards tab when its selection changed, so a multi-selection survives tab switches
+        var lastSyncedCardSelection;
         var updatePermissionCardSelection = function() {
-            var matchingCard = correspondingCard(viewModel.cardTree.selection(), viewModel.permissionTree);
+            var cardSelection = viewModel.cardTree.selection();
+            if (cardSelection === lastSyncedCardSelection) {
+                return;
+            }
+            lastSyncedCardSelection = cardSelection;
+            var matchingCard = correspondingCard(cardSelection, viewModel.permissionTree);
             if (matchingCard) {
                 viewModel.permissionTree.expandToRoot(matchingCard);
                 viewModel.permissionTree.selection.removeAll();
-                matchingCard.selectChildCards();
+                matchingCard.selectChildCards(true);
             }
         };


```

## 60. kitsune: `CG-QUAL-104` (new_but_matched)

- Commit: [59b6937db5](https://github.com/mozilla/kitsune/commit/59b6937db573505c764bec9c87bd786981848487), file `kitsune/sumo/static/sumo/js/markup.js`
- Truth: **new**, new line 844
- Schemes that disagree with the truth: `codeguard` (false_known)

After:

```
   840      var kbox;
   841
   842      var cannedResponsesUrl = "/kb/common-forum-responses";
   843      var previewBtn = document.getElementById("preview");
>  844      var siteLanguage = window.location.pathname.split("/")[1];
   845      var previewUrl = previewBtn
   846        ? previewBtn.dataset.previewUrl
   847        : "/" + siteLanguage + "/questions/answer-preview-async";
   848
```

Diff near the line:

```diff
@@ -840,7 +840,11 @@ Marky.CannedResponsesButton.prototype = Object.assign({}, Marky.SimpleButton.pro
     var kbox;

     var cannedResponsesUrl = "/kb/common-forum-responses";
-    var previewUrl = "answer-preview-async";
+    var previewBtn = document.getElementById("preview");
+    var siteLanguage = window.location.pathname.split("/")[1];
+    var previewUrl = previewBtn
+      ? previewBtn.dataset.previewUrl
+      : "/" + siteLanguage + "/questions/answer-preview-async";

     function updatePreview() {
       var response = html.querySelector("#response-content").value;

```

## 61. ckan: `CG-QUAL-104` (agree_known)

- Commit: [fd309bc144](https://github.com/ckan/ckan/commit/fd309bc144f08505087d8b8d463aa8da296ba766), file `ckan/public/base/javascript/client.js`
- Truth: **known (equal)**, old line 227, new line 226
- Schemes that disagree with the truth: none

Before:

```
   223        var packages = jQuery.trim(string).split('\n');
   224        var parsed = [];
   225
   226        return jQuery.map(packages, function (pkg) {
>  227          var parts = pkg.split('|');
   228          var id    = jQuery.trim(parts.pop() || '');
   229          var text  = jQuery.trim(parts.join('|') || '');
   230          return options && options.objects === true ? {id: id, text: text} : id;
   231        });
```
After:

```
   222        var packages = jQuery.trim(string).split('\n');
   223        var parsed = [];
   224
   225        return jQuery.map(packages, function (pkg) {
>  226          var parts = pkg.split('|');
   227          var id    = jQuery.trim(parts.pop() || '');
   228          var text  = jQuery.trim(parts.join('|') || '');
   229          return options && options.objects === true ? {id: id, text: text} : id;
   230        });
```

## 62. hoppscotch: `CG-QUAL-101` (agree_known)

- Commit: [1855faabbc](https://github.com/hoppscotch/hoppscotch/commit/1855faabbc4ff968d874f54510f6c586a7fdae05), file `packages/hoppscotch-common/src/lib/sync/collections/index.ts`
- Truth: **known (equal)**, old line 796, new line 799
- Schemes that disagree with the truth: none

Before:

```
   792          description,
   793          preRequestScript,
   794          testScript,
   795        } =
>  796          data && data != "null"
   797            ? JSON.parse(data)
   798            : {
   799                auth: { authType: "inherit", authActive: true },
   800                headers: [],
```
After:

```
   795          description,
   796          preRequestScript,
   797          testScript,
   798        } =
>  799          data && data != "null"
   800            ? JSON.parse(data)
   801            : {
   802                auth: { authType: "inherit", authActive: true },
   803                headers: [],
```

## 63. indico: `CG-QUAL-003` (agree_known)

- Commit: [1ab29e1359](https://github.com/indico/indico/commit/1ab29e13596cacf234ce75f7c0d4be217010ba6d), file `indico/modules/events/registration/util.py`
- Truth: **known (equal)**, old line 474, new line 474
- Schemes that disagree with the truth: none

Before:

```
   470      return registration
   471
   472
   473  @no_autoflush
>  474  def modify_registration(registration, data, management=False, notify_user=True):
   475      from indico.modules.events.registration.tasks import delete_previous_registration_file
   476
   477      user = session.user if session else None
   478      old_data = snapshot_registration_data(registration)
```
After:

```
   470      return registration
   471
   472
   473  @no_autoflush
>  474  def modify_registration(registration, data, management=False, notify_user=True):
   475      from indico.modules.events.registration.tasks import delete_previous_registration_file
   476
   477      user = session.user if session else None
   478      old_data = snapshot_registration_data(registration)
```

## 64. securedrop: `CG-QUAL-003` (agree_known)

- Commit: [871378be59](https://github.com/freedomofpress/securedrop/commit/871378be59567ac2916c1ae5d8f347784288d46f), file `securedrop/tests/test_journalist_api2.py`
- Truth: **known (equal)**, old line 738, new line 738
- Schemes that disagree with the truth: none

Before:

```
   734          )
   735          assert response.json["events"][stale_event.id] == [200, None]
   736
   737
>  738  def test_api2_source_deleted(
   739      journalist_app,
   740      journalist_api_token,
   741      test_files,
   742  ):
```
After:

```
   734          )
   735          assert response.json["events"][stale_event.id] == [200, None]
   736
   737
>  738  def test_api2_source_deleted(
   739      journalist_app,
   740      journalist_api_token,
   741      test_files,
   742  ):
```

## 65. weblate: `CG-QUAL-004` (agree_known)

- Commit: [f4e6cc3fe0](https://github.com/WeblateOrg/weblate/commit/f4e6cc3fe00e4ea1c0dd849af897442246f14191), file `weblate/trans/tests/test_autotranslate.py`
- Truth: **known (equal)**, old line 1621, new line 1639
- Schemes that disagree with the truth: none

Before:

```
  1617          translation = self.component3.translation_set.get(language_code="cs")
  1618          translation.invalidate_cache()
  1619          self.assertEqual(translation.stats.translated, expected)
  1620
> 1621      def test_component_help_matches_scope_and_accepted_inputs(self) -> None:
  1622          workspace = Workspace.objects.create(name="Automatic translation workspace")
  1623          self.project.workspace = workspace
  1624          self.project.save(update_fields=["workspace"])
  1625          original_values_list = ComponentQuerySet.values_list
```
After:

```
  1635          translation = self.component3.translation_set.get(language_code="cs")
  1636          translation.invalidate_cache()
  1637          self.assertEqual(translation.stats.translated, expected)
  1638
> 1639      def test_component_help_matches_scope_and_accepted_inputs(self) -> None:
  1640          workspace = Workspace.objects.create(name="Automatic translation workspace")
  1641          self.project.workspace = workspace
  1642          self.project.save(update_fields=["workspace"])
  1643          original_values_list = ComponentQuerySet.values_list
```

## 66. securedrop: `CG-SEC-002` (agree_known)

- Commit: [db86920ded](https://github.com/freedomofpress/securedrop/commit/db86920ded3273f0fec3f7cb7287817bf5167000), file `securedrop/tests/test_journalist.py`
- Truth: **known (equal)**, old line 1339, new line 1338
- Schemes that disagree with the truth: none

Before:

```
  1335
  1336
  1337  def test_user_resets_hotp(journalist_app, test_journo):
  1338      old_secret = test_journo["otp_secret"]
> 1339      new_secret = "0123456789ABCDEF0123456789ABCDEF01234567"
  1340
  1341      # Precondition
  1342      assert new_secret != old_secret
  1343
```
After:

```
  1334
  1335
  1336  def test_user_resets_hotp(journalist_app, test_journo):
  1337      old_secret = test_journo["otp_secret"]
> 1338      new_secret = "0123456789ABCDEF0123456789ABCDEF01234567"
  1339
  1340      # Precondition
  1341      assert new_secret != old_secret
  1342
```

## 67. arches: `CG-QUAL-003` (agree_known)

- Commit: [ef3a5efc29](https://github.com/archesproject/arches/commit/ef3a5efc290afac95e3a6b5e3c8edabd51a9ddab), file `arches/app/permissions/arches_default_deny.py`
- Truth: **known (equal)**, old line 230, new line 264
- Schemes that disagree with the truth: none

Before:

```
   226          should_access.should(principal_user_term_filter)
   227          has_access.filter(should_access)
   228          return has_access
   229
>  230      def get_search_ui_permissions(
   231          self, user: User, search_result: dict, groups: list[str]
   232      ) -> dict:
   233          result = {}
   234
```
After:

```
   260          should_access.should(principal_user_term_filter)
   261          has_access.filter(should_access)
   262          return has_access
   263
>  264      def get_search_ui_permissions(
   265          self, user: User, search_result: dict, groups: list[str]
   266      ) -> dict:
   267          result = {}
   268
```

## 68. habitica: `CG-SEC-111` (agree_known)

- Commit: [78c62a5aec](https://github.com/HabitRPG/habitica/commit/78c62a5aec6f6270ff432de6fdb6efb0e120526d), file `website/server/controllers/api-v3/tasks.js`
- Truth: **known (equal)**, old line 1017, new line 1018
- Schemes that disagree with the truth: none

Before:

```
  1013
  1014      const item = find(task.checklist, { id: req.params.itemId });
  1015      if (!item) throw new NotFound(res.t('checklistItemNotFound'));
  1016
> 1017      merge(item, Tasks.Task.sanitizeChecklist(req.body));
  1018      const savedTask = await task.save();
  1019
  1020      res.respond(200, savedTask);
  1021      if (challenge) challenge.updateTask(savedTask);
```
After:

```
  1014
  1015      const item = find(task.checklist, { id: req.params.itemId });
  1016      if (!item) throw new NotFound(res.t('checklistItemNotFound'));
  1017
> 1018      merge(item, Tasks.Task.sanitizeChecklist(req.body));
  1019      const savedTask = await task.save();
  1020
  1021      res.respond(200, savedTask);
  1022      if (challenge) challenge.updateTask(savedTask);
```

## 69. arches: `CG-QUAL-104` (agree_known)

- Commit: [719e7c189d](https://github.com/archesproject/arches/commit/719e7c189df8cc023d756198938d60b280be9c61), file `arches/app/media/js/views/graph-designer.js`
- Truth: **known (equal)**, old line 775, new line 777
- Schemes that disagree with the truth: none

Before:

```
   771          };
   772
   773          var updateCardSelection = function() {
   774              var graphTreeSelection = viewModel.graphTree.selectedItems().length > 0 ? viewModel.graphTree.selectedItems()[0] : null;
>  775              var matchingCard;
   776              if (graphTreeSelection) {
   777                  if (graphTreeSelection.istopnode === true) {
   778                      viewModel.cardTree.selection(viewModel.cardTree.topCards()[0]);
   779                  } else {
```
After:

```
   773          };
   774
   775          var updateCardSelection = function() {
   776              var graphTreeSelection = viewModel.graphTree.selectedItems().length > 0 ? viewModel.graphTree.selectedItems()[0] : null;
>  777              var matchingCard;
   778              if (graphTreeSelection) {
   779                  if (graphTreeSelection.istopnode === true) {
   780                      viewModel.cardTree.selection(viewModel.cardTree.topCards()[0]);
   781                  } else {
```

## 70. inventree: `CG-QUAL-003` (agree_known)

- Commit: [5244b8a4f2](https://github.com/inventree/InvenTree/commit/5244b8a4f21436f699ea266eb5a7381f899409f0), file `src/backend/InvenTree/plugin/registry.py`
- Truth: **known (equal)**, old line 688, new line 689
- Schemes that disagree with the truth: none

Before:

```
   684
   685      # endregion
   686
   687      # region general internal loading / activating / deactivating / unloading
>  688      def _init_plugin(self, plugin, configs: dict):
   689          """Initialise a single plugin.
   690
   691          Args:
   692              plugin: Plugin module
```
After:

```
   685
   686      # endregion
   687
   688      # region general internal loading / activating / deactivating / unloading
>  689      def _init_plugin(self, plugin, configs: dict):
   690          """Initialise a single plugin.
   691
   692          Args:
   693              plugin: Plugin module
```

## 71. readthedocs: `CG-SEC-002` (agree_known)

- Commit: [6b9919fd28](https://github.com/readthedocs/readthedocs.org/commit/6b9919fd2891a30f9f75a99c81fd71d6f09bb821), file `readthedocs/rtd_tests/tests/test_api.py`
- Truth: **known (equal)**, old line 762, new line 759
- Schemes that disagree with the truth: none

Before:

```
   758
   759      def test_create_key_for_project_with_long_slug(self):
   760          user = get(User)
   761          project = get(Project, users=[user], slug="a" * 60)
>  762          build_api_key_obj, build_api_key = BuildAPIKey.objects.create_key(project)
   763          self.assertTrue(BuildAPIKey.objects.is_valid(build_api_key))
   764          self.assertEqual(build_api_key_obj.name, "a" * 50)
   765
   766      def test_revoke_build_api_key(self):
```
After:

```
   755
   756      def test_create_key_for_project_with_long_slug(self):
   757          user = get(User)
   758          project = get(Project, users=[user], slug="a" * 60)
>  759          build_api_key_obj, build_api_key = BuildAPIKey.objects.create_key(project)
   760          self.assertTrue(BuildAPIKey.objects.is_valid(build_api_key))
   761          self.assertEqual(build_api_key_obj.name, "a" * 50)
   762
   763      def test_revoke_build_api_key(self):
```

## 72. arches: `CG-QUAL-104` (agree_known)

- Commit: [fbfb7c9092](https://github.com/archesproject/arches/commit/fbfb7c909265301e0945f9bad49f5c68ae2a76da), file `arches/app/media/js/viewmodels/map-editor.js`
- Truth: **known (equal)**, old line 358, new line 359
- Schemes that disagree with the truth: none

Before:

```
   354          map.jumpTo(camera);
   355      };
   356
   357      this.editGeoJSON = function (features, nodeId) {
>  358          var geoJSONString = JSON.stringify(
   359              {
   360                  type: "FeatureCollection",
   361                  features: features,
   362              },
```
After:

```
   355          map.jumpTo(camera);
   356      };
   357
   358      this.editGeoJSON = function (features, nodeId) {
>  359          var geoJSONString = JSON.stringify(
   360              {
   361                  type: "FeatureCollection",
   362                  features: features,
   363              },
```

## 73. defectdojo: `CG-QUAL-104` (agree_known)

- Commit: [7e2af4942c](https://github.com/DefectDojo/django-DefectDojo/commit/7e2af4942cfddf89ecace7bffb35c0d006d76a53), file `dojo/static/dojo/js/metrics.js`
- Truth: **known (equal)**, old line 836, new line 836
- Schemes that disagree with the truth: none

Before:

```
   832      var min = opts.min || 0;
   833      var range = max - min;
   834      var pct = range > 0 ? ((value - min) / range) * 100 : 0;
   835      var remaining = 100 - pct;
>  836      var title = opts.title || '';
   837      var label = opts.label || '';
   838
   839      // Pick colour based on percentage
   840      var color;
```
After:

```
   832      var min = opts.min || 0;
   833      var range = max - min;
   834      var pct = range > 0 ? ((value - min) / range) * 100 : 0;
   835      var remaining = 100 - pct;
>  836      var title = opts.title || '';
   837      var label = opts.label || '';
   838
   839      // Pick colour based on percentage
   840      var color;
```

## 74. ckan: `CG-QUAL-003` (agree_known)

- Commit: [ea3c0fd881](https://github.com/ckan/ckan/commit/ea3c0fd8814de0fa83e744bcb4d5ab5a93902a34), file `ckan/logic/action/update.py`
- Truth: **known (equal)**, old line 474, new line 500
- Schemes that disagree with the truth: none

Before:

```
   470
   471      return pkg_custom
   472
   473
>  474  def package_revise(context: Context, data_dict: DataDict) -> ActionResult.PackageRevise:
   475      '''Revise a dataset (package) selectively with match, filter and
   476      update parameters.
   477
   478      You must be authorized to edit the dataset and the groups that it belongs
```
After:

```
   496
   497      return pkg_custom
   498
   499
>  500  def package_revise(context: Context, data_dict: DataDict) -> ActionResult.PackageRevise:
   501      '''Revise a dataset (package) selectively with match, filter and
   502      update parameters.
   503
   504      You must be authorized to edit the dataset and the groups that it belongs
```

## 75. geonode: `CG-SEC-002` (agree_known)

- Commit: [e653caf78f](https://github.com/GeoNode/geonode/commit/e653caf78f3567996934967448a7e959db44236e), file `geonode/utils.py`
- Truth: **known (equal)**, old line 1061, new line 1061
- Schemes that disagree with the truth: none

Before:

```
  1057          self.backoff_factor = 0.3
  1058          self.pool_connections = 10
  1059          self.status_forcelist = (500, 502, 503, 504)
  1060          self.username = "admin"
> 1061          self.password = "admin"
  1062          if check_ogc_backend(geoserver.BACKEND_PACKAGE):
  1063              ogc_server_settings = settings.OGC_SERVER["default"]
  1064              self.timeout = ogc_server_settings.get("TIMEOUT", 5)
  1065              self.retries = ogc_server_settings.get("MAX_RETRIES", 1)
```
After:

```
  1057          self.backoff_factor = 0.3
  1058          self.pool_connections = 10
  1059          self.status_forcelist = (500, 502, 503, 504)
  1060          self.username = "admin"
> 1061          self.password = "admin"
  1062          if check_ogc_backend(geoserver.BACKEND_PACKAGE):
  1063              ogc_server_settings = settings.OGC_SERVER["default"]
  1064              self.timeout = ogc_server_settings.get("TIMEOUT", 5)
  1065              self.retries = ogc_server_settings.get("MAX_RETRIES", 1)
```

## 76. geonode: `CG-QUAL-002` (agree_known)

- Commit: [e653caf78f](https://github.com/GeoNode/geonode/commit/e653caf78f3567996934967448a7e959db44236e), file `geonode/utils.py`
- Truth: **known (equal)**, old line 377, new line 377
- Schemes that disagree with the truth: none

Before:

```
   373              if ":" in dataset.alternate:
   374                  _name = dataset.alternate.split(":")[1]
   375              else:
   376                  _name = dataset.alternate
>  377      except Exception:
   378          pass
   379      return _name
   380
   381
```
After:

```
   373              if ":" in dataset.alternate:
   374                  _name = dataset.alternate.split(":")[1]
   375              else:
   376                  _name = dataset.alternate
>  377      except Exception:
   378          pass
   379      return _name
   380
   381
```

## 77. erpnext: `CG-QUAL-005` (agree_known)

- Commit: [028a9ed1d9](https://github.com/frappe/erpnext/commit/028a9ed1d94ce99702dd65b32ca3aede52b52006), file `erpnext/stock/doctype/pick_list/pick_list.py`
- Truth: **known (equal)**, old line 1354, new line 1451
- Schemes that disagree with the truth: none

Before:

```
  1350  	item_location_map[item_doc.item_code] = available_locations
  1351  	return locations
  1352
  1353
> 1354  def get_available_item_locations(
  1355  	item_code,
  1356  	from_warehouses,
  1357  	required_qty,
  1358  	company,
```
After:

```
  1447  	item_location_map[item_doc.item_code] = available_locations
  1448  	return locations
  1449
  1450
> 1451  def get_available_item_locations(
  1452  	item_code,
  1453  	from_warehouses,
  1454  	required_qty,
  1455  	company,
```

## 78. kitsune: `CG-QUAL-104` (agree_known)

- Commit: [7558489f48](https://github.com/mozilla/kitsune/commit/7558489f48358f1f90ab0dfd5e4cc1a285240693), file `kitsune/sumo/static/sumo/js/markup.js`
- Truth: **known (equal)**, old line 421, new line 568
- Schemes that disagree with the truth: none

Before:

```
   417          '</ol><div class="submit sumo-button-wrap align-full reverse-on-desktop"><button type="button" class="sumo-button primary-button"></button>' +
   418          '<a href="#cancel" class="kbox-cancel sumo-button secondary-button">' + gettext("Cancel") +
   419          "</a></div></section>"
   420      );
>  421      var selectedText = me.getSelectedText();
   422      var kbox;
   423
   424      html.querySelectorAll('li input[type="text"]').forEach(function (input) {
   425        input.addEventListener("focus", function () {
```
After:

```
   564          '</ol><div class="submit sumo-button-wrap align-full reverse-on-desktop"><button type="button" class="sumo-button primary-button"></button>' +
   565          '<a href="#cancel" class="kbox-cancel sumo-button secondary-button">' + gettext("Cancel") +
   566          "</a></div></section>"
   567      );
>  568      var selectedText = me.getSelectedText();
   569      var kbox;
   570
   571      html.querySelectorAll('li input[type="text"]').forEach(function (input) {
   572        input.addEventListener("focus", function () {
```

## 79. inventree: `CG-QUAL-101` (agree_known)

- Commit: [02da01dfec](https://github.com/inventree/InvenTree/commit/02da01dfec309ac410e846a57d329d0e96b90e21), file `src/frontend/src/pages/stock/TransferOrderDetail.tsx`
- Truth: **known (equal)**, old line 160, new line 166
- Schemes that disagree with the truth: none

Before:

```
   156            order.status != toStatus.COMPLETE
   157              ? t`Allocated Stock`
   158              : t`Transferred Stock`,
   159          icon:
>  160            order.status != toStatus.COMPLETE ? (
   161              <IconBookmark />
   162            ) : (
   163              <IconListCheck />
   164            ),
```
After:

```
   162            order.status != toStatus.COMPLETE
   163              ? t`Allocated Stock`
   164              : t`Transferred Stock`,
   165          icon:
>  166            order.status != toStatus.COMPLETE ? (
   167              <IconBookmark />
   168            ) : (
   169              <IconListCheck />
   170            ),
```

## 80. kitsune: `CG-QUAL-104` (agree_known)

- Commit: [59b6937db5](https://github.com/mozilla/kitsune/commit/59b6937db573505c764bec9c87bd786981848487), file `kitsune/sumo/static/sumo/js/markup.js`
- Truth: **known (equal)**, old line 633, new line 633
- Schemes that disagree with the truth: none

Before:

```
   629      this.closeTag = "";
   630      this.defaultText = "";
   631    },
   632    openModal: function (ev) {
>  633      var me = this;
   634      var editorEl = me.textarea.closest(".editor");
   635      var mediaSearchUrl = editorEl ? editorEl.dataset.mediaSearchUrl : undefined;
   636      var galleryUrl = editorEl ? editorEl.dataset.mediaGalleryUrl : "";
   637      var html = parseHTML(
```
After:

```
   629      this.closeTag = "";
   630      this.defaultText = "";
   631    },
   632    openModal: function (ev) {
>  633      var me = this;
   634      var editorEl = me.textarea.closest(".editor");
   635      var mediaSearchUrl = editorEl ? editorEl.dataset.mediaSearchUrl : undefined;
   636      var galleryUrl = editorEl ? editorEl.dataset.mediaGalleryUrl : "";
   637      var html = parseHTML(
```

## 81. ckan: `CG-QUAL-104` (agree_new)

- Commit: [9c010ae0a9](https://github.com/ckan/ckan/commit/9c010ae0a9dca9967292563ad856ca99079b891f), file `ckan/public/base/javascript/modules/autocomplete.js`
- Truth: **new**, new line 77
- Schemes that disagree with the truth: none

After:

```
    73            settings.multiple = "multiple"
    74
    75            // tokenizer is not applied when custom data adapter is used
    76            if (settings.tokenSeparators != null) {
>   77              var Tokenizer = $.fn.select2.amd.require('select2/data/tokenizer');
    78              settings.dataAdapter = Utils.Decorate(settings.dataAdapter, Tokenizer);
    79            }
    80          }
    81
```

Diff near the line:

```diff
@@ -50,33 +49,52 @@ this.ckan.module('autocomplete', function (jQuery) {
     setupAutoComplete: function () {
       var settings = {
         width: 'resolve',
-        formatResult: this.formatResult,
-        formatNoMatches: this.formatNoMatches,
-        formatInputTooShort: this.formatInputTooShort,
-        formatSearching: this.formatSearching,
+        templateResult: this.templateResult,
+        language: {
+          noResults: this.formatNoMatches,
+          inputTooShort: this.formatInputTooShort,
+          searching: this.formatSearching,
+        },
         dropdownCssClass: this.options.dropdownClass,
-        containerCssClass: this.options.containerClass,
         tokenSeparators: this.options.tokensep.split(''),
-        minimumInputLength: this.options.minimumInputLength
+        minimumInputLength: this.options.minimumInputLength,
+        selectionCssClass: this.options.containerClass
       };

       // Different keys are required depending on whether the select is
       // tags or generic completion.
       if (!this.el.is('select')) {
-        if (this.options.tags) {
-          settings.tags = this._onQuery;
-
-          // Disable creating new tags
-          if (!this.options.createtags) {
-            settings.createSearchChoice = function(params) {
-              return undefined;
-            }
+
+        settings.dataAdapter = this.dataAdapter();
+        if ( this.options.tags ){
+          var Utils = $.fn.select2.amd.require('select2/utils');
+          var Tags = $.fn.select2.amd.require('select2/data/tags');
+          settings.dataAdapter = Utils.Decorate(settings.dataAdapter, Tags)
+          settings.multiple = "multiple"
... (31 more lines)
```

## 82. lnbits: `CG-SEC-105` (agree_new)

- Commit: [653924a6dc](https://github.com/lnbits/lnbits/commit/653924a6dcb6d821a9dae32cd9aac5d287351c57), file `lnbits/static/i18n/fo.js`
- Truth: **new**, new line 300
- Schemes that disagree with the truth: none

After:

```
   296    notifications_configure: 'Fráboðanaruppsetan',
   297    notifications_nostr_config: 'Nostr uppsetan',
   298    notifications_enable_nostr: 'Virkja Nostr fráboðanir',
   299    notifications_enable_nostr_desc: 'Send fráboðanir umvegis Nostr',
>  300    notifications_nostr_private_key: 'Nostr privatur lykil',
   301    notifications_nostr_private_key_desc:
   302      'Privatur lykil, í sekstandatal ella nsec skapi, at undirrita boð send til Nostr',
   303    notifications_nostr_identifier: 'Nostr-dátuheiti',
   304    notifications_nostr_identifier_desc:
```

Diff near the line:

```diff
@@ -0,0 +1,901 @@
+window.localisation.fo = {
+  confirm: 'Ja',
+  server: 'Ambætari',
+  theme: 'Snið',
+  site_customisation: 'Vevsíðu tillagingar',
+  funding: 'Fígging',
+  users: 'Brúkarar',
+  audit: 'Slóðfesti',
+  api_watch: 'API nýtsluyvirlit',
+  apps: 'Appir',
+  channels: 'Rásir',
+  transactions: 'Flytingar',
+  dashboard: 'Yvirlitssýni',
+  node: 'Knútur',
+  export_users: 'Tak brúkarar út',
+  no_users: 'Eingin brúkari finst',
+  total_capacity: 'Samlað rásarupphædd',
+  avg_channel_size: 'Miðal rásarupphædd',
+  biggest_channel_size: 'Størsta rásarupphædd',
+  smallest_channel_size: 'Minsta rásarupphædd',
+  number_of_channels: 'Tal av rásum',
+  active_channels: 'Virknar rásir',
+  connect_peer: 'Sambind við javninga',
+  connect: 'Sambind',
+  reconnect: 'Sambind aftur',
+  open_channel: 'Ger rás',
+  open: 'Lat upp',
+  clear: 'Tómstilla',
+  close_channel: 'Loka rás',
+  close: 'Loka',
+  restart: 'Endurbyrja ambætara',
+  image_library: 'Myndasavn',
+  save: 'Goym',
+  save_tooltip: 'Goym broytingarnar',
+  must_save: 'Tú hevur framt broytingar ið enn ikki eru goymdar.',
+  credit_debit: 'Góðskriva / Skuldskriva',
+  credit_hint:
+    'Trýst á Enter til tess at góðskriva/skuldskriva mappu (negativ viðri eru loyvd)',
+  credit_label: '{denomination} at góðskriva/skuldskriva',
... (863 more lines)
```

## 83. openlibrary: `CG-QUAL-003` (agree_new)

- Commit: [ff9577a078](https://github.com/internetarchive/openlibrary/commit/ff9577a078ac1492c1ce4cef0bd53b69e98a692e), file `openlibrary/bookworm/cli.py`
- Truth: **new**, new line 406
- Schemes that disagree with the truth: none

After:

```
   402          return MATCHED_EXPECTED, matched_key, expected
   403      return MATCHED_OTHER, matched_key, expected
   404
   405
>  406  def preview_command(
   407      ol_config: str = "/openlibrary/conf/openlibrary.yml",
   408      provider: str = "",
   409      limit: int | None = None,
   410      expect_edition_ids: bool = True,
```

Diff near the line:

```diff
@@ -0,0 +1,520 @@
+#!/usr/bin/env python
+"""Command line for the BookWorm feed harvest (#12844).
+
+Three commands, all needing ``--ol-config`` because it supplies both the
+database connection and -- on hosts that egress through a proxy -- the settings
+without which no provider feed is reachable at all::
+
+    python -m openlibrary.bookworm.cli harvest  --ol-config /olsystem/etc/openlibrary.yml
+    python -m openlibrary.bookworm.cli register --ol-config /olsystem/etc/openlibrary.yml --show
+    python -m openlibrary.bookworm.cli preview  --ol-config /olsystem/etc/openlibrary.yml --provider lenny
+
+``harvest`` is the cron entrypoint: one pass over every active feed, then exit,
+so the crontab can see a non-zero status. ``register`` puts the feed list in git
+rather than in hand-typed SQL. ``preview`` reports what the catalog would match
+without writing anything, for diagnosing a feed that looks wrong.
+
+Run ``<command> --help`` for each one's options. The harvest logic itself is in
+``harvest.py``; this module is only the interface to it.
+"""
+
+import datetime
+import logging
+import sys
+import time
+from collections import Counter
+from collections.abc import Callable
+from urllib.parse import urlparse
+
+from infogami import config
+from openlibrary.bookworm import harvest
+from openlibrary.bookworm.registry import (
+    CURSOR_MODIFIED_SINCE,
+    STATUS_ACTIVE,
+    FeedRegistry,
+)
+from openlibrary.catalog.add_book import load
+from openlibrary.config import load_config
+from openlibrary.plugins.upstream.utils import setup_requests
+from scripts.solr_builder.solr_builder.fn_to_cli import FnToCLI
... (482 more lines)
```

## 84. inventree: `CG-QUAL-101` (agree_new)

- Commit: [99893f3453](https://github.com/inventree/InvenTree/commit/99893f3453c6a213a331c022e82cbafbde7ebd51), file `src/frontend/src/components/tables/InvenTreeTable.tsx`
- Truth: **new**, new line 940
- Schemes that disagree with the truth: none

After:

```
   936          params: queryParams,
   937          timeout: 10 * 1000
   938        })
   939        .then((response) => {
>  940          if (generation != nestedGeneration.current) {
   941            return;
   942          }
   943
   944          let results = response.data?.results ?? response.data ?? [];
```

Diff near the line:

```diff
@@ -776,6 +862,170 @@ export function InvenTreeTableInternal<T extends Record<string, any>>({
     tableState.setRecords(tableData ?? apiData ?? []);
   }, [tableData, apiData]);

+  // Serialized params, so that nested data is not discarded on every render
+  const paramsKey: string = useMemo(
+    () => JSON.stringify(tableProps.params ?? {}),
+    [tableProps.params]
+  );
+
+  // Discard nested data whenever the top-level table data is reloaded,
+  // or the nesting configuration changes (as child rows depend on it)
+  useEffect(() => {
+    nestedGeneration.current += 1;
+    // Keep the existing (empty) state object to avoid a needless re-render
+    setNestedState((state) => (Object.keys(state).length > 0 ? {} : state));
+  }, [
+    props.nestedRows,
+    url,
+    tableData,
+    apiData,
+    paramsKey,
+    pageSize,
+    sortStatus,
+    tableState.page,
+    tableState.searchTerm,
+    tableState.tableKey,
+    tableState.filterSet.activeFilters,
+    tableSearchParams
+  ]);
+
+  // Expand or collapse a nested row, fetching child rows if required
+  toggleNestedRow.current = (record: T) => {
+    const nestedRows = props.nestedRows;
+
+    if (!nestedRows || !url) {
+      return;
+    }
+
+    const key = getRowKey(record);
... (131 more lines)
```

## 85. calcom: `CG-QUAL-103` (agree_new)

- Commit: [0d164da8dd](https://github.com/calcom/cal.com/commit/0d164da8ddc68474300dc85677856950ef81ee7e), file `apps/web/playwright/fixtures/users.ts`
- Truth: **new**, new line 813
- Schemes that disagree with the truth: none

After:

```
   809    profileUsername?: string;
   810  };
   811
   812  // creates the actual user in the db.
>  813  const createUser = (
   814    workerInfo: WorkerInfo,
   815    opts?:
   816      | (CustomUserOpts & {
   817          organizationId?: number | null;
```

Diff near the line:

```diff
(no diff hunk near this line)
```

## 86. erpnext: `CG-QUAL-104` (agree_new)

- Commit: [8c85cef29b](https://github.com/frappe/erpnext/commit/8c85cef29b0b80a23a499516a94d4319cf45503d), file `erpnext/stock/doctype/landed_cost_voucher/landed_cost_voucher.js`
- Truth: **new**, new line 119
- Schemes that disagree with the truth: none

After:

```
   115  				});
   116
   117  				var charge_precision = precision("applicable_charges", items[0]);
   118  				var total = flt(this.frm.doc.total_taxes_and_charges);
>  119  				var sign = total < 0 ? -1 : 1;
   120  				var diff = flt(total - total_charges, charge_precision);
   121  				for (const item of items.slice().reverse()) {
   122  					if (!diff) break;
   123  					var share = flt(item.applicable_charges) * sign;
```

Diff near the line:

```diff
@@ -114,9 +114,19 @@ erpnext.stock.LandedCostVoucher = class LandedCostVoucher extends erpnext.stock.
 					total_charges += item.applicable_charges;
 				});

-				if (total_charges != this.frm.doc.total_taxes_and_charges) {
-					var diff = this.frm.doc.total_taxes_and_charges - flt(total_charges);
-					items.slice(-1)[0].applicable_charges += diff;
+				var charge_precision = precision("applicable_charges", items[0]);
+				var total = flt(this.frm.doc.total_taxes_and_charges);
+				var sign = total < 0 ? -1 : 1;
+				var diff = flt(total - total_charges, charge_precision);
+				for (const item of items.slice().reverse()) {
+					if (!diff) break;
+					var share = flt(item.applicable_charges) * sign;
+					var adjustment = diff * sign > 0 ? diff : sign * Math.max(diff * sign, -share);
+					item.applicable_charges = flt(
+						flt(item.applicable_charges) + adjustment,
+						charge_precision
+					);
+					diff = flt(diff - adjustment, charge_precision);
 				}
 				refresh_field("items");
 			}

```

## 87. hoppscotch: `CG-PERF-101` (agree_new)

- Commit: [e633b55a0b](https://github.com/hoppscotch/hoppscotch/commit/e633b55a0b9da30f3d6ddefcc9ab3c393cd52be8), file `packages/hoppscotch-common/src/services/__tests__/ai-chat-ui.spec.ts`
- Truth: **new**, new line 325
- Schemes that disagree with the truth: none

After:

```
   321        ]
   322
   323        for (const prompt of prompts) {
   324          chat.pendingConfirmation.value = null
>  325          await nextTick()
   326          i18n.keys.length = 0
   327          chat.pendingConfirmation.value = {
   328            name: "A",
   329            workspace: null,
```

Diff near the line:

```diff
@@ -0,0 +1,996 @@
+/* eslint-disable vue/one-component-per-file */
+import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
+import { TestContainer } from "dioc/testing"
+import { diocPlugin } from "dioc/vue"
+import * as E from "fp-ts/Either"
+import { BehaviorSubject } from "rxjs"
+import { createApp, defineComponent, h, nextTick, ref, type App } from "vue"
+import { createMemoryHistory, createRouter } from "vue-router"
+
+vi.mock("~/modules/i18n", () => ({
+  getI18n: () => (key: string) => key,
+  APP_LANGUAGES: [],
+  changeAppLanguage: () => {},
+}))
+// Records each key; params show as "key(a|b)" so a test can see them.
+const i18n = vi.hoisted(() => ({ keys: [] as string[] }))
+vi.mock("~/composables/i18n", () => ({
+  useI18n: () => (key: string, params?: Record<string, unknown>) => {
+    i18n.keys.push(key)
+    return params ? `${key}(${Object.values(params).join("|")})` : key
+  },
+}))
+
+const ai = vi.hoisted(() => ({
+  enableAIExperiments: true,
+  chat: undefined as unknown,
+  getChatAvailability: undefined as unknown,
+  generateRequestName: undefined as unknown,
+}))
+// A fresh stream per test, so services from earlier tests stop listening.
+const auth = vi.hoisted(() => ({
+  user$: null as null | { value: unknown; next(v: unknown): void },
+}))
+vi.mock("~/platform", () => ({
+  platform: {
+    experiments: { aiExperiments: ai },
+    auth: {
+      getCurrentUser: () => auth.user$!.value,
+      getCurrentUserStream: () => auth.user$,
... (958 more lines)
```

## 88. lnbits: `CG-QUAL-003` (agree_new)

- Commit: [7eb9965205](https://github.com/lnbits/lnbits/commit/7eb996520584b3da9ed865c944e11ddbd2095998), file `tests/api/test_admin_api.py`
- Truth: **new**, new line 151
- Schemes that disagree with the truth: none

After:

```
   147      server_restart.clear()
   148
   149
   150  @pytest.mark.anyio
>  151  async def test_admin_delete_settings_requires_superuser(
   152      client: AsyncClient, superuser_token: str
   153  ):
   154      await set_settings_field("lnbits_site_title", "Reset me")
   155      await set_settings_field("lnbits_backend_wallet_class", "BoltzWallet")
```

Diff near the line:

```diff
@@ -150,6 +151,15 @@ async def test_admin_partial_reset_restart_and_backup(
 async def test_admin_delete_settings_requires_superuser(
     client: AsyncClient, superuser_token: str
 ):
+    await set_settings_field("lnbits_site_title", "Reset me")
+    await set_settings_field("lnbits_backend_wallet_class", "BoltzWallet")
+    await set_settings_field("boltz_mnemonic", "keep boltz seed")
+    await set_settings_field("boltz_mnemonic_backup_confirmed", True)
+    await set_settings_field("phoenixd_mnemonic", "keep phoenixd seed")
+    await set_settings_field("phoenixd_mnemonic_backup_confirmed", True)
+    await set_settings_field("spark_l2_mnemonic", "keep spark seed")
+    await set_settings_field("spark_l2_mnemonic_backup_confirmed", True)
+
     server_restart.clear()
     response = await client.delete(
         "/admin/api/v1/settings",
```

## 89. netbox: `CG-SEC-001` (agree_new)

- Commit: [9d96894f4e](https://github.com/netbox-community/netbox/commit/9d96894f4e1c622c25de40ccca5847efa5e15153), file `netbox/utilities/tests/test_ltree.py`
- Truth: **new**, new line 1184
- Schemes that disagree with the truth: none

After:

```
  1180
  1181      def drop_cascade_trigger(self):
  1182          """Leave the table as a database restored from a v4.7.0 dump: no cascade trigger."""
  1183          with connection.cursor() as cursor:
> 1184              cursor.execute(f'DROP TRIGGER IF EXISTS "{self.TRIGGER}" ON "{self.TABLE}"')
  1185
  1186      def install_v470_cascade_trigger(self):
  1187          """
  1188          Install the definition v4.7.0 shipped: bare ltree comparisons, which a dump cannot
```

Diff near the line:

```diff
@@ -992,3 +996,240 @@ class RestrictedSearchPathBackfillTests(TestCase):

         self.assertEqual(len(plain_rows), 2)
         self.assertEqual([r[0] for r in plain_rows], [_path(1), _path(1, 2)])
+
+
+class RestoreUnderRestrictedSearchPathTests(TestCase):
+    """
+    The generated trigger DDL must create with the ltree extension's schema off the
+    search_path, because that is how pg_dump replays it: dumps begin with
+    `set_config('search_path', '', false)` and schema-qualify every name they can.
+
+    `IS DISTINCT FROM` cannot be schema-qualified — it expands to the operand type's
+    `=` operator, resolved at CREATE TRIGGER time — so comparing two ltree values in a
+    WHEN clause produced a cascade trigger which silently failed to restore, leaving
+    descendant paths to go stale on the next rename or reparent (#23130). Comparing
+    `path::text` resolves `pg_catalog.text =` instead, which is always available.
+
+    The trigger functions are created with the extension's schema on the path: they
+    legitimately declare `parent_path ltree`, and pg_dump schema-qualifies those
+    declarations, so only the CREATE TRIGGER statements are under test here.
+    """
+
+    def _install_with_extension_off_path(self, schema, table, name_column):
+        with connection.cursor() as cursor:
+            cursor.execute(f'CREATE SCHEMA {schema}')
+            columns = 'id bigint PRIMARY KEY, parent_id bigint, path ltree, name text'
+            if name_column:
+                columns += ', sort_path text'
+            cursor.execute(f'SET LOCAL search_path = {schema}, public')
+            cursor.execute(f'CREATE TABLE {schema}.{table} ({columns})')
+
+            statements = ltree_trigger_sql(table, name_column)
+            functions = [s for s in statements if 'CREATE OR REPLACE FUNCTION' in s]
+            triggers = [s for s in statements if 'CREATE TRIGGER' in s]
+            self.assertEqual(len(functions), 2)
+            self.assertEqual(len(triggers), 2)
+
+            # Pass an empty parameter list, as schema_editor.execute() does during a
+            # migration: the function bodies double their literal percent signs for
... (202 more lines)
```

## 90. lnbits: `CG-PERF-101` (agree_new)

- Commit: [c0806ca59c](https://github.com/lnbits/lnbits/commit/c0806ca59c90464e424f881a92efd8033fd9bd2b), file `tests/e2e/extension-helpers.ts`
- Truth: **new**, new line 540
- Schemes that disagree with the truth: none

After:

```
   536    await expect(tab).toBeVisible({timeout: 60_000})
   537    for (let attempt = 0; attempt < 3; attempt += 1) {
   538      await tab.click()
   539      try {
>  540        await expect(tab).toHaveAttribute('aria-selected', 'true', {
   541          timeout: 5_000
   542        })
   543        return
   544      } catch (_error) {
```

Diff near the line:

```diff
@@ -0,0 +1,658 @@
+import {expect, type Frame, type Locator, type Page} from '@playwright/test'
+
+import {
+  browserJson,
+  delay,
+  isRecord,
+  type LNbitsE2EServer,
+  waitForResult
+} from './fixtures'
+
+const INSTALLABLE_EXTENSION_REFRESH_TASK =
+  'refresh_installable_extensions_cache'
+
+export type ExtensionUnderTest = {
+  extId: string
+  manifestUrl: string
+  name: string
+  permissionTexts?: string[]
+  repository: string
+}
+
+export type E2EWallet = {
+  adminkey: string
+  id: string
+  inkey: string
+  name: string
+}
+
+export async function login(
+  page: Page,
+  server: LNbitsE2EServer
+): Promise<void> {
+  await page.goto('/')
+  await page.locator('input[name="username"]').fill(server.username)
+  await page.locator('input[name="password"]').fill(server.password)
+  await page.getByRole('button', {name: /^login$/i}).click()
+  await expect(page).toHaveURL(/\/wallet\/[^/]+$/)
+  await dismissDisclaimer(page)
+}
... (620 more lines)
```

## 91. calcom: `CG-SEC-105` (agree_new)

- Commit: [089a39f59f](https://github.com/calcom/cal.com/commit/089a39f59f39f4cd613ab0064dc23117b080c538), file `apps/api/v2/src/ee/bookings/2024-08-13/controllers/e2e/update-booking-location.e2e-spec.ts`
- Truth: **new**, new line 529
- Schemes that disagree with the truth: none

After:

```
   525
   526        it("can update location to type integration (office365-video)", async () => {
   527          const office365Credential = await credentialsRepositoryFixture.create(
   528            "office365_calendar",
>  529            { access_token: "mock", refresh_token: "mock", expiry_date: Date.now() + 3600000 },
   530            testSetup.organizer.id,
   531            "office365-calendar"
   532          );
   533
```

Diff near the line:

```diff
@@ -322,6 +387,219 @@ describe("Bookings Endpoints 2024-08-13 update booking location", () => {
         expect(updatedBooking.location).toEqual(attendeeDefinedLocation);
       });

+      it("can update location to type integration (cal-video)", async () => {
+        const updatedBookingBody: UpdateBookingLocationInput_2024_08_13 = {
+          location: {
+            type: "integration",
+            integration: "cal-video",
+          },
+        };
+
+        const updatedBookingResponse = await request(app.getHttpServer())
+          .patch(`/v2/bookings/${bookingUid}/location`)
+          .send(updatedBookingBody)
+          .set(CAL_API_VERSION_HEADER, VERSION_2024_08_13)
+          .set("Authorization", `Bearer ${testSetup.organizer.accessToken}`)
+          .expect(200);
+
+        const updatedBookingResponseBody: UpdateBookingLocationOutput_2024_08_13 =
+          updatedBookingResponse.body;
+        expect(updatedBookingResponseBody.status).toEqual(SUCCESS_STATUS);
+        if (!responseDataIsBooking(updatedBookingResponseBody.data)) {
+          throw new Error(
+            "Invalid response data - expected booking but received array of possibly recurring bookings"
+          );
+        }
+        const updatedBooking = updatedBookingResponseBody.data as BookingOutput_2024_08_13;
+        expect(updatedBooking).toHaveProperty("id");
+        // cal-video location should be either a Daily video URL or the internal location string
+        expect(
+          updatedBooking.location?.startsWith("http") || updatedBooking.location === "integrations:daily"
+        ).toBe(true);
+      });
+
+      it("can update location to type integration (google-meet)", async () => {
+        const googleCredential = await credentialsRepositoryFixture.create(
+          "google_calendar",
+          { access_token: "mock", refresh_token: "mock", expiry_date: Date.now() + 3600000 },
+          testSetup.organizer.id,
... (181 more lines)
```

## 92. edx-platform: `CG-SEC-002` (agree_new)

- Commit: [294f05f57e](https://github.com/openedx/edx-platform/commit/294f05f57e3ba73c59b31394cbc2f2c9d6808c14), file `cms/djangoapps/contentstore/rest_api/v1/views/tests/test_course_index.py`
- Truth: **new**, new line 279
- Schemes that disagree with the truth: none

After:

```
   275
   276      @override_waffle_flag(core_toggles.AUTHZ_COURSE_AUTHORING_FLAG, active=False)
   277      def test_reindex_link_absent_for_course_staff_without_global_staff(self):
   278          """A course-staff member who isn't Global Staff does not see the reindex link."""
>  279          course_staff_user, password = self.create_non_staff_user()
   280          CourseStaffRole(self.course.id).add_users(course_staff_user)
   281
   282          client = AjaxEnabledTestClient()
   283          client.login(username=course_staff_user.username, password=password)
```

Diff near the line:

```diff
@@ -224,3 +226,72 @@ class CourseIndexAuthzViewTest(CourseAuthoringAuthzTestMixin, CourseTestCase):

         assert response.status_code == status.HTTP_200_OK
         assert "course_structure" in response.data
+
+
+class CourseIndexViewReindexLinkAuthzTest(CourseAuthoringAuthzTestMixin, CourseTestCase):
+    """
+    Regression tests: with AuthZ course authoring enabled, `reindex_link` (and therefore the
+    Reindex button in the course-authoring MFE) must follow the same access rules as the actual
+    reindex action, not be restricted to Global Staff only.
+    """
+
+    def setUp(self):
+        super().setUp()
+        self.url = reverse("cms.djangoapps.contentstore:v1:course_index", kwargs={"course_id": self.course.id})
+
+    def test_reindex_link_present_for_non_global_staff_with_authz_permission(self):
+        """A non-global-staff user granted the AuthZ course-staff role sees the reindex link."""
+        self.add_user_to_role_in_course(self.authorized_user, COURSE_STAFF.external_key, self.course.id)
+
+        response = self.authorized_client.get(self.url)
+
+        assert response.status_code == status.HTTP_200_OK
+        assert not self.authorized_user.is_staff
+        assert response.data["reindex_link"] == f"/course/{self.course.id}/search_reindex"
+
+    def test_reindex_link_absent_without_reindex_permission(self):
+        """
+        A user with enough AuthZ permission to view the course (COURSE_EDITOR) but without the
+        publish-content permission required to reindex does not see the reindex link.
+        """
+        self.add_user_to_role_in_course(self.authorized_user, COURSE_EDITOR.external_key, self.course.id)
+
+        response = self.authorized_client.get(self.url)
+
+        assert response.status_code == status.HTTP_200_OK
+        assert response.data["reindex_link"] is None
+
+
... (34 more lines)
```

## 93. uptime-kuma: `CG-PERF-101` (agree_new)

- Commit: [e62702d868](https://github.com/louislam/uptime-kuma/commit/e62702d868a0b072c6e1870e5278762319637f04), file `server/notification-providers/indigo.js`
- Truth: **new**, new line 52
- Schemes that disagree with the truth: none

After:

```
    48              }
    49              config = this.getAxiosConfigWithProxy(config);
    50
    51              for (const command of commands) {
>   52                  const result = await axios.post(url, { id: "uptime-kuma", ...command }, config);
    53                  if (result.data?.error || result.data?.validationErrors) {
    54                      throw new Error(
    55                          `Indigo rejected ${command.message}: ${result.data.error || JSON.stringify(result.data.validationErrors)}`
    56                      );
```

Diff near the line:

```diff
@@ -0,0 +1,67 @@
+const NotificationProvider = require("./notification-provider");
+const axios = require("axios");
+const https = require("https");
+
+class Indigo extends NotificationProvider {
+    name = "Indigo";
+
+    /**
+     * @inheritdoc
+     */
+    async send(notification, msg, monitorJSON = null, heartbeatJSON = null) {
+        const okMsg = "Sent Successfully.";
+        const url = `${notification.indigoUrl.trim().replace(/\/*$/, "")}/v2/api/command`;
+        const variableId = parseInt(notification.indigoVariableId);
+        const actionGroupId = parseInt(notification.indigoActionGroupId);
+
+        if (!variableId && !actionGroupId) {
+            throw new Error("Set an Indigo variable ID, an action group ID, or both.");
+        }
+
+        // The variable is written first so the action group can read it.
+        const commands = [];
+        if (variableId) {
+            commands.push({
+                message: "indigo.variable.updateValue",
+                objectId: variableId,
+                parameters: { value: msg },
+            });
+        }
+        if (actionGroupId) {
+            commands.push({
+                message: "indigo.actionGroup.execute",
+                objectId: actionGroupId,
+            });
+        }
+
+        try {
+            let config = {
+                headers: {
... (29 more lines)
```

## 94. lnbits: `CG-QUAL-005` (agree_new)

- Commit: [61ed636df0](https://github.com/lnbits/lnbits/commit/61ed636df066ced4c600a5eb55af147e6d13d130), file `lnbits/core/services/extensions.py`
- Truth: **new**, new line 268
- Schemes that disagree with the truth: none

After:

```
   264                  settings.lnbits_wasm_invocation_retention_days
   265              )
   266
   267
>  268  async def start_wasm_invocation(
   269      *,
   270      extension_id: str,
   271      export_name: str,
   272      trigger_type: str = "unknown",
```

Diff near the line:

```diff
@@ -75,6 +245,394 @@ async def check_extensions_limit(installed_ext: InstallableExtension | None = No
         raise ValueError("Max amount of extensions have been installed")


+async def ensure_wasm_invocation_monitoring_ready() -> None:
+    global _wasm_invocations_last_cleanup_at, _wasm_invocations_marked_stale
+
+    async with _wasm_invocation_ready_lock:
+        now = _now()
+        if not _wasm_invocations_marked_stale:
+            await mark_stale_wasm_invocations()
+            _wasm_invocations_marked_stale = True
+
+        if (
+            _wasm_invocations_last_cleanup_at is None
+            or now - _wasm_invocations_last_cleanup_at
+            >= _WASM_INVOCATION_CLEANUP_INTERVAL
+        ):
+            _wasm_invocations_last_cleanup_at = now
+            await delete_old_wasm_invocations(
+                settings.lnbits_wasm_invocation_retention_days
+            )
+
+
+async def start_wasm_invocation(
+    *,
+    extension_id: str,
+    export_name: str,
+    trigger_type: str = "unknown",
+    user_id: str | None = None,
+    wallet_id: str | None = None,
+    request_id: str | None = None,
+    method: str | None = None,
+    path: str | None = None,
+    event_type: str | None = None,
+    payment_hash: str | None = None,
+    checking_id: str | None = None,
+    request_bytes: int | None = None,
+    context: dict | None = None,
+    runtime_limits: dict[str, int] | None = None,
... (355 more lines)
```

## 95. netbox: `CG-SEC-001` (agree_new)

- Commit: [8cc4548e1f](https://github.com/netbox-community/netbox/commit/8cc4548e1f51fcd4cb63299339b55e5ef179e28a), file `netbox/utilities/ltree.py`
- Truth: **new**, new line 287
- Schemes that disagree with the truth: none

After:

```
   283              schema_editor.execute(_AFTER_TRIGGER_PATH_ONLY.format(table=self.table_name))
   284
   285      def database_backwards(self, app_label, schema_editor, from_state, to_state):
   286          t = self.table_name
>  287          schema_editor.execute(f'DROP TRIGGER IF EXISTS "{t}_ltree_cascade_path" ON "{t}";')
   288          schema_editor.execute(f'DROP TRIGGER IF EXISTS "{t}_ltree_compute_path" ON "{t}";')
   289          schema_editor.execute(f'DROP FUNCTION IF EXISTS "{t}_ltree_cascade_path_fn"();')
   290          schema_editor.execute(f'DROP FUNCTION IF EXISTS "{t}_ltree_compute_path_fn"();')
   291
```

Diff near the line:

```diff
@@ -0,0 +1,293 @@
+"""
+Migration support for ltree-based hierarchical models.
+
+This module holds the schema-level machinery that backs `netbox.models.ltree`:
+the PostgreSQL trigger function / trigger SQL and the `InstallLtreeTriggers`
+migration operation that installs them. It is kept separate from the model layer
+(`netbox.models.ltree`) so that migrations depend only on this DB-level code and
+not on the model definitions.
+
+The paths maintained by these triggers are never computed or mutated from Python;
+the model layer only reads `path`/`sort_path` back from the database.
+"""
+from django.db import migrations
+
+__all__ = (
+    'InstallLtreeTriggers',
+)
+
+
+# Path label is the row's PK zero-padded to 19 chars (max bigint width) so that
+# lexicographic ordering of ltree labels matches numeric PK ordering across digit
+# boundaries (e.g. "0...09" sorts before "0...10").
+# Per-tree advisory locking (see _lock_tree_roots_sql / LtreeModel "Concurrency"):
+# every child insert / move / reparent of a node takes a transaction-level
+# advisory lock keyed on the root(s) of the tree(s) it touches, BEFORE reading the
+# parent path. A concurrent reparent of an ancestor takes the same key, so the two
+# serialize and the AFTER cascade can never miss a row inserted concurrently;
+# writes in different trees use different keys and run in parallel. Inserting a new
+# root (parent_id IS NULL) takes no lock at all -- it is a race-free singleton tree
+# -- so a bulk import of many top-level objects does not accumulate one lock per
+# root and cannot exhaust the shared lock table.
+_LOCK_TREE_ROOTS_SQL = '''
+    -- A brand-new root (INSERT with parent_id IS NULL) starts its own singleton
+    -- tree that no concurrent transaction can yet see (MVCC: the uncommitted row
+    -- is invisible) or reference (no other transaction has its PK). For such a
+    -- row this BEFORE function reads no other row (the parent lookup below is
+    -- gated on parent_id) and the AFTER cascade fires only on UPDATE, so the
+    -- insert touches solely its own NEW row -- there is nothing to serialize
+    -- against, and the advisory lock it would otherwise take can never contend.
... (255 more lines)
```

## 96. ckan: `CG-SEC-103` (agree_new)

- Commit: [1902693db4](https://github.com/ckan/ckan/commit/1902693db45f27bd6a4b93fb0f16b83bba5f79b8), file `ckan/public/base/javascript/toast.js`
- Truth: **new**, new line 162
- Schemes that disagree with the truth: none

After:

```
   158      wrapper.setAttribute("role", opts.style === "danger" ? "alert" : "status");
   159      wrapper.setAttribute("aria-live", opts.style === "danger" ? "assertive" : "polite");
   160      wrapper.setAttribute("aria-atomic", "true");
   161
>  162      wrapper.innerHTML = `<div id="${containerID}" class="toast-container position-fixed pb-1 ${positionClasses}"></div>`;
   163      document.body.appendChild(wrapper);
   164
   165      return document.getElementById(containerID);
   166    };
```

Diff near the line:

```diff
@@ -0,0 +1,193 @@
+(function (ckan, $) {
+
+  /**
+   * Displays Bootstrap 5 toast notifications across CKAN
+   *
+   * Usage:
+   *
+   * ckan.toast({
+   *    message: "Operation completed successfully",
+   *    type: "success",
+   *    title: "Done",
+   *    icon: "<i class='fa fa-check-circle me-2'></i>",
+   *    subtitle: "Just now",
+   *    delay: 5000,
+   *    position: "bottom-right"
+   *    stacking: false
+   * });
+   *
+   *
+   * Options:
+   * - message   (string)  [required] The main message body of the toast.
+   * - type      (string)  Optional.  Defines toast style, matches keys from `styles`. Default: "default".
+   * - title     (string)  Optional.  Text shown in the toast header.
+   * - icon      (string)  Optional.  HTML for an icon displayed before the title.
+   * - subtitle  (string)  Optional.  Text shown in the header's small subtitle area.
+   * - delay     (number)  Optional.  Time in milliseconds before auto-hide. Default: 3000.
+   * - position  (string)  Optional.  Position key controlling toast placement. Default: "bottom-right".
+   * - showProgress  (boolean) Optional.  Whether to show a progress bar. Default: false.
+   * - stacking  (boolean) Optional.  Whether to stack toasts on top of each other. Default: true.
+  */
+  var toast = function (options) {
+    if (!options || !options.message) {
+      console.error("Toast: Missing required 'message' option.");
+      return;
+    }
+
+    const opts = {
+      type: "default",
+      title: "",
... (155 more lines)
```

## 97. healthchecks: `CG-QUAL-104` (agree_new)

- Commit: [b83e3791d6](https://github.com/healthchecks/healthchecks/commit/b83e3791d6e2c276a13c0b40c2e435c6ec01125c), file `hc/integrations/po/static/js/add_pushover.js`
- Truth: **new**, new line 7
- Schemes that disagree with the truth: none

After:

```
     3          var parts = item.text.split(":");
     4          return `<div>${parts[0]}. <span class="help">${parts[1]}</span></div>`;
     5      }
     6
>    7      var config = {
     8          maxItems: 1,
     9          controlInput: null,
    10          plugins: ["no_backspace_delete"],
    11          render: {option: makeOption, item: makeOption},
```

Diff near the line:

```diff
@@ -1,8 +1,17 @@
 $(function() {
     function makeOption(item, escape) {
         var parts = item.text.split(":");
-        return `<div class="option">${parts[0]}. <span class="help">${parts[1]}</span></div>`;
+        return `<div>${parts[0]}. <span class="help">${parts[1]}</span></div>`;
     }

-    $("select").selectize({render: {option: makeOption, item: makeOption}});
+    var config = {
+        maxItems: 1,
+        controlInput: null,
+        plugins: ["no_backspace_delete"],
+        render: {option: makeOption, item: makeOption},
+    };
+
+    document.querySelectorAll("select").forEach((el) => {
+        new TomSelect(el, config)
+    });
 });
\ No newline at end of file

```

## 98. hoppscotch: `CG-PERF-101` (agree_new)

- Commit: [e633b55a0b](https://github.com/hoppscotch/hoppscotch/commit/e633b55a0b9da30f3d6ddefcc9ab3c393cd52be8), file `packages/hoppscotch-common/src/services/ai-chat.service.ts`
- Truth: **new**, new line 4893
- Schemes that disagree with the truth: none

After:

```
  4889          )
  4890        } else {
  4891          request._ref_id = generateUniqueRefId("req")
  4892          delete (request as { id?: string }).id
> 4893          const res = await createRequestInCollection(found.node.id, {
  4894            request: JSON.stringify(request),
  4895            teamID,
  4896            title: request.name,
  4897          })()
```

Diff near the line:

```diff
@@ -0,0 +1,6825 @@
+import { Service } from "dioc"
+import {
+  computed,
+  nextTick,
+  ref,
+  shallowRef,
+  watch,
+  type ShallowRef,
+} from "vue"
+import * as E from "fp-ts/Either"
+import type {
+  HoppCollection,
+  HoppCollectionVariable,
+  HoppGQLRequest,
+  HoppRESTAuth,
+  HoppRESTHeader,
+  HoppRESTRequest,
+} from "@hoppscotch/data"
+import { populateValuesInInheritedCollectionVars } from "~/helpers/utils/inheritedCollectionVarTransformer"
+import {
+  Environment,
+  EnvironmentSchemaVersion,
+  generateUniqueRefId,
+  isRESTRequest,
+  makeCollection,
+  translateToNewEnvironmentVariables,
+} from "@hoppscotch/data"
+import { pipe } from "fp-ts/function"
+import * as TE from "fp-ts/TaskEither"
+import { TeamCollectionsService } from "~/services/team-collection.service"
+import type { TeamCollection } from "~/helpers/teams/TeamCollection"
+import type { TeamRequest } from "~/helpers/teams/TeamRequest"
+import type { TeamEnvironment } from "~/helpers/teams/TeamEnvironment"
+import type { HoppInheritedProperty } from "~/helpers/types/HoppInheritedProperties"
+import {
+  getCompleteCollectionTree,
+  teamCollToHoppRESTColl,
+} from "~/helpers/backend/helpers"
+import {
... (6787 more lines)
```

## 99. arches: `CG-QUAL-104` (agree_new)

- Commit: [2e02ce6e61](https://github.com/archesproject/arches/commit/2e02ce6e61999d93c10b05d853ae08f1912fa294), file `arches/app/media/js/views/graph/permission-designer.js`
- Truth: **new**, new line 157
- Schemes that disagree with the truth: none

After:

```
   153                          }
   154
   155                          var inherited = nodegroup.explicit.length === 0;
   156                          var sourceLabel = describeSource(nodegroup.source);
>  157                          var perms = nodegroup.effective.map(function(perm) {
   158                              return {
   159                                  codename: perm.codename,
   160                                  name: perm.name,
   161                                  icon: permIcons[perm.codename],
```

Diff near the line:

```diff
@@ -70,62 +99,82 @@ import PermissionSettingsForm from 'views/graph/permission-manager/permission-se
                         self.updatePermissions();
                     });
                 })
-                .fail(function(err) {
-                    console.log(err);
+                .fail(function(response) {
+                    showError(response.responseJSON, arches.translations.graphDesignerPermissionsLoadError);
+                })
+                .always(function() {
+                    self.loading(false);
                 });
         };

+        var setCardPerms = function(card, perms, literal) {
+            card.perms(perms);
+            card.permsLiteral(literal);
+            if (card.type === 'card' && card.children && card.children.length > 0) {
+                card.children.forEach(function(child) {
+                    if (child.type === 'node' && child.perms) {
+                        child.perms(perms);
+                    }
+                });
+            }
+        };
+
         this.updatePermissions = function() {
-            var item = self.identityList.selectedItems()[0];
-            var nodegroupIds = [];
+            var identity = self.identityList.selectedItems()[0];

-            if (item) {
-                self.cardList.forEach(function(item) {
-                    nodegroupIds.push(item.model.nodegroup_id());
+            if (!identity || !self.cardList) {
+                self.permissionsByNodegroup({});
+                (self.cardList || []).forEach(function(card) {
+                    setCardPerms(card, [], '');
                 });
-                $.ajax({
... (91 more lines)
```

## 100. healthchecks: `CG-QUAL-004` (agree_new)

- Commit: [cb1926beda](https://github.com/healthchecks/healthchecks/commit/cb1926bedaeca358a644e3096cd47d80648abfd3), file `hc/integrations/telegram/transport.py`
- Truth: **new**, new line 30
- Schemes that disagree with the truth: none

After:

```
    26          description: str
    27          parameters: Telegram.MigrationParameters | None = None
    28
    29      @classmethod
>   30      def raise_for_response(cls, response: curl.Response) -> NoReturn:
    31          message = f"Received status code {response.status_code}"
    32          try:
    33              m = Telegram.ErrorModel.model_validate_json(response.content)
    34          except ValidationError:
```

Diff near the line:

```diff
(no diff hunk near this line)
```
