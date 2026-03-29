Components
- phantom omni connector to track user movement
- metrics calculation engine for metrics like jitter, path efficiency, time to completion
- database to store movement data (unstructured) and calculated metrics along with run info such as user and test performed (structured)

Database
- movement data (unstructured json): store points as time,x,y,z and outer with user, scenario, and date time metadata
- metrics data (structured table): user performance metrics and run id which is generated as a combination of user_scenario_datetime for ease of matching of data in the future
- analysis is performed using movement data, which is then populated to metrics data

Happy path (UX)
1. user selects scenario (test1/test2/training)
2. user begins scenario on unity
3. user completes scenario (groups with and without haptic guidance)
4. user movement is recorded and performance is calculated and tracked
5. user repeats steps 2-4 for defined x number of times (training)
6. once ready, user tests on the test scenario for y number of times
7. user test data is recorded and analysed for performance improvement

Happy path (tech stack)
1. server is started and calibrated to the correct user and scenario and haptic enablement (ie test 1)
2. ideal path is loaded for comparison (and haptic guidance for the test group)
3. user begins scenario on unity (websocket is fired to server to begin)
4. for test group, user is consistently linearly guided towards the next movement coordinate
5. for both, user's own jitter, path efficiency and drift from the ideal movement path is calculated
6. upon completion, websocket sigint is fired to the server, terminating the guidance as well as movement recording.
7. movement session is stored as structured and unstructured data with appropriate naming to session (user, scenario, haptic enablement)

For analysis
1. database can be queried for user + scenario performed + metric
2. the metric can then be plotted across the appropriate attempts performed
3. test metric should be plotted separately

Assets
- Matthew's ideal scenario movement (timing should be evenly distributed over 15, 10, 5s) (joint xyz are the target columns of movement)